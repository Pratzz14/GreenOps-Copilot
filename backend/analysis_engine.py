"""Read-only SQL validation, visual query compilation, and isolated execution."""
import multiprocessing as mp
from datetime import date, datetime
from decimal import Decimal
from math import isfinite
from time import monotonic
from typing import Literal

import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

from backend.analysis_data import unit_key

MAX_ROWS = 10_000
BUDGET = 5
AGGREGATES = {"count": "COUNT", "distinct": "COUNT", "sum": "SUM", "mean": "AVG",
              "min": "MIN", "max": "MAX", "median": "MEDIAN"}
SCALARS = {"ABS", "AVG", "CAST", "CEIL", "COALESCE", "CONTAINS", "COUNT", "DATE_TRUNC", "FLOOR",
           "LENGTH", "LOWER", "MAX", "MEDIAN", "MIN", "NULLIF", "ROUND", "SUM", "TIMESTAMP_TRUNC",
           "UPPER"}
NODES = set("""
Select Alias Column Identifier Literal Boolean Null Star From Table TableAlias Where Group Having
Order Ordered Limit Offset With CTE Subquery Distinct Paren EQ NEQ LT LTE GT GTE And Or Not Is In
Between Like ILike Filter Add Sub Mul Div Neg Mod DataType DataTypeParam Var
""".split())


class Filter(BaseModel):
    field: str
    op: Literal["eq", "in", "contains", "lt", "lte", "gt", "gte", "range", "null", "not_null"]
    values: list[str] = Field(default_factory=list, max_length=50)


class Dimension(BaseModel):
    field: str
    month: bool = False


class Metric(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    op: Literal["rows", "count", "distinct", "sum", "mean", "min", "max", "median", "calculate"]
    field: str = ""
    left: str = ""
    right: str = ""
    operator: Literal["+", "-", "*", "/"] = "/"


class Visual(BaseModel):
    columns: list[str] = Field(default_factory=list, max_length=100)
    filters: list[Filter] = Field(default_factory=list, max_length=30)
    groups: list[Dimension] = Field(default_factory=list, max_length=12)
    metrics: list[Metric] = Field(default_factory=list, max_length=30)
    sort: str = ""
    descending: bool = False
    limit: int | None = Field(default=None, ge=1, le=MAX_ROWS)


def identifier(name):
    return '"' + name.replace('"', '""') + '"'


def literal(value, kind):
    if kind == "decimal" or kind == "integer":
        number = Decimal(value)
        if not number.is_finite() or abs(number.adjusted()) > 30:
            raise ValueError("Enter a finite number with at most 30 decimal places")
        if kind == "integer" and number != number.to_integral_value():
            raise ValueError("Enter a whole number")
        return format(number, "f")
    if kind == "boolean":
        if value.lower() not in {"true", "false"}:
            raise ValueError("Enter true or false")
        return value.upper()
    if kind == "date":
        return f"CAST('{date.fromisoformat(value).isoformat()}' AS DATE)"
    return exp.Literal.string(value).sql(dialect="duckdb")


def compile_visual(dataset, columns, definition):
    def field(name):
        if name not in columns:
            raise ValueError(f"Unknown field {name!r}")
        return identifier(name)

    clauses = []
    fixed = set()
    for rule in definition.filters:
        column = field(rule.field)
        kind = columns[rule.field]
        op = rule.op
        if op in ("null", "not_null"):
            clauses.append(f"{column} IS {'NOT ' if op == 'not_null' else ''}NULL")
            continue
        if op in {"lt", "lte", "gt", "gte", "range"} and kind not in {"date", "decimal", "integer"}:
            raise ValueError("Ordered filters require a date or numeric field")
        values = [literal(value, kind) for value in rule.values]
        if len(values) != (2 if op == "range" else 1) and not (op == "in" and values):
            raise ValueError(f"Supply values for {rule.field} ({op})")
        if op == "contains":
            if kind not in {"text", "category"}:
                raise ValueError("Contains requires a text field")
            clauses.append(f"CONTAINS({column}, {values[0]})")
        elif op == "range":
            clauses.append(f"{column} BETWEEN {values[0]} AND {values[1]}")
        elif op == "in":
            clauses.append(f"{column} IN ({', '.join(values)})")
            if len(values) == 1:
                fixed.add(rule.field)
        else:
            operator = {"eq": "=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}[op]
            clauses.append(f"{column} {operator} {values[0]}")
            if op == "eq":
                fixed.add(rule.field)
    group_fields = {group.field for group in definition.groups if not group.month}

    def compatible(name):
        key = unit_key(dataset, name, columns)
        if key and key not in fixed | group_fields:
            raise ValueError(f"Group by {key} or filter it to one value before aggregating {name}")

    groups = []
    projections = []
    names = []
    for group in definition.groups:
        column = field(group.field)
        if group.month and columns[group.field] != "date":
            raise ValueError("Month grouping requires a date field")
        expr = f"DATE_TRUNC('month', {column})" if group.month else column
        name = f"{group.field}_month" if group.month else group.field
        names.append(name)
        projections.append(f"{expr} AS {identifier(name)}")
        groups.append(expr)
    for metric in definition.metrics:
        op = metric.op
        if op == "rows":
            expr = "COUNT(*)"
        elif op == "calculate":
            left, right = field(metric.left), field(metric.right)
            if any(columns[name] not in {"integer", "decimal"} for name in (metric.left, metric.right)):
                raise ValueError("Calculated metrics require numeric fields")
            from backend.analysis_data import unit
            if metric.operator in {"+", "-"} and (
                unit(dataset, metric.left) != unit(dataset, metric.right)
                or unit_key(dataset, metric.left, columns) != unit_key(dataset, metric.right, columns)
            ):
                raise ValueError("Addition and subtraction require compatible units")
            compatible(metric.left)
            compatible(metric.right)
            if definition.groups or any(item.op != "calculate" for item in definition.metrics):
                raise ValueError("Calculated metrics operate on individual rows. Aggregate them in an SQL subquery.")
            if metric.operator == "/":
                right = f"NULLIF({right}, 0)"
            expr = f"{left} {metric.operator} {right}"
        else:
            column = field(metric.field)
            if op not in {"count", "distinct"}:
                if columns[metric.field] not in {"decimal", "integer"}:
                    raise ValueError(f"{op} requires a numeric field")
                compatible(metric.field)
            expr = f"{AGGREGATES[op]}({'DISTINCT ' if op == 'distinct' else ''}{column})"
        names.append(metric.name)
        projections.append(f"{expr} AS {identifier(metric.name)}")
    if not groups and all(metric.op == "calculate" for metric in definition.metrics):
        selected = definition.columns or list(columns)
        names = selected + names
        projections = [field(name) for name in selected] + projections
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Output names must be unique")
    sql = f"SELECT {', '.join(projections)}\nFROM {identifier(dataset)}"
    if clauses:
        sql += "\nWHERE " + " AND ".join(clauses)
    if groups:
        sql += "\nGROUP BY " + ", ".join(groups)
    if definition.sort:
        if definition.sort not in names:
            raise ValueError("Sort by an output field")
        sql += f"\nORDER BY {identifier(definition.sort)} {'DESC' if definition.descending else 'ASC'}"
    if definition.limit:
        sql += f"\nLIMIT {definition.limit}"
    return sql


def validate_sql(sql, dataset):
    statements = sqlglot.parse(sql, read="duckdb")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("Enter one SELECT statement")
    tree = statements[0]
    for node in tree.walk():
        if type(node).__name__ not in NODES:
            if not isinstance(node, exp.Func):
                raise ValueError(f"Unsupported SQL expression: {type(node).__name__}")
            name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
            if name not in SCALARS:
                raise ValueError(f"Unsupported SQL function: {name}")
        if isinstance(node, exp.With) and node.args.get("recursive"):
            raise ValueError("Recursive CTEs are unavailable")
        if isinstance(node, exp.Table) and (node.catalog or node.db or not isinstance(node.this, exp.Identifier)):
            raise ValueError("Use an unqualified registered dataset")
        if isinstance(node, exp.CTE) and node.alias.casefold() == dataset.casefold():
            raise ValueError("Use a CTE name different from the dataset")
    found = False
    for scope in traverse_scope(tree):
        for _, source in scope.selected_sources.values():
            if isinstance(source, exp.Table):
                if source.name.casefold() != dataset.casefold():
                    raise ValueError(f"Query only the selected dataset ({dataset})")
                if source.this.args.get("quoted") and source.name != dataset:
                    source.set("this", exp.to_identifier(dataset, quoted=True))
                found = True
    if not found:
        raise ValueError(f"Select from {dataset}")
    return tree


def direct_projection(tree, columns):
    """Identify simple projections whose units and lineage survive unchanged."""
    source = tree.args.get("from_")
    if tree.args.get("with_") or not source or not isinstance(source.this, exp.Table):
        return {}
    projected = {}
    for item in tree.expressions:
        value = item.this if isinstance(item, exp.Alias) else item
        if isinstance(value, exp.Star) or isinstance(value, exp.Column) and value.is_star:
            projected.update({name: name for name in columns})
        elif isinstance(value, exp.Column) and value.name.lower() in columns:
            projected[item.output_name] = value.name.lower()
    return projected


def sql_type(kind, values):
    if kind == "decimal":
        decimals = [Decimal(value) for value in values if value is not None]
        scale = max([0] + [-value.as_tuple().exponent for value in decimals])
        whole_digits = max([1] + [value.adjusted() + 1 for value in decimals])
        if scale + whole_digits > 38:
            raise ValueError("Silver decimal exceeds DuckDB’s exact decimal capacity")
        return f"DECIMAL(38,{scale})"
    return {"date": "DATE", "boolean": "BOOLEAN", "integer": "BIGINT"}.get(kind, "VARCHAR")


def cell(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not isfinite(value):
        return None
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) >= 2**53:
        return str(value)
    return value


def worker(pipe, dataset, columns, rows, sql):
    try:
        import duckdb
        import pandas as pd

        config = dict(enable_external_access="false", autoinstall_known_extensions="false",
                      autoload_known_extensions="false", threads="2", memory_limit="256MB",
                      temp_directory="", lock_configuration="true")
        with duckdb.connect(":memory:", config=config) as engine:
            values = {key: [row.get(key) for row in rows] for key in columns}
            casts = [f"CAST({identifier(key)} AS {sql_type(kind, values[key])}) AS {identifier(key)}"
                     for key, kind in columns.items()]
            frame = pd.DataFrame({key: pd.array([str(v) if v is not None else None for v in column], dtype="string")
                                  for key, column in values.items()})
            engine.register("trusted_input", frame)
            engine.execute(f"CREATE TABLE {identifier(dataset)} AS SELECT {', '.join(casts)} FROM trusted_input")
            engine.unregister("trusted_input")
            pipe.send(("ready", None))
            cursor = engine.execute(f"SELECT * FROM ({sql}) AS analysis_result LIMIT {MAX_ROWS + 1}")
            fields = [(info[0], str(info[1])) for info in cursor.description]
            result = [[cell(value) for value in row] for row in cursor.fetchall()]
            pipe.send(("ok", (fields, result[:MAX_ROWS], len(result) > MAX_ROWS)))
    except Exception as error:
        pipe.send(("error", str(error)))
    finally:
        pipe.close()


def execute(dataset, columns, rows, sql):
    context = mp.get_context("spawn")
    reader, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(sender, dataset, columns, rows, sql), daemon=True)
    try:
        process.start()
        sender.close()
        if not reader.poll(20):
            raise TimeoutError("Could not initialize the Silver query worker")
        status, result = reader.recv()
        if status == "error":
            raise ValueError(result)
        start = monotonic()
        if not reader.poll(BUDGET):
            raise TimeoutError("Query exceeded five seconds. Add a filter or simplify the query.")
        status, result = reader.recv()
        if status == "error":
            raise ValueError(result)
        return (*result, round((monotonic() - start) * 1000))
    except EOFError as error:
        raise ValueError("Query worker stopped unexpectedly. Try a smaller query.") from error
    finally:
        sender.close()
        reader.close()
        if process.pid is not None:
            process.join(0.1)
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
