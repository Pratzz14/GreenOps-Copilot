"""Local Silver analyst queries, cached exports and saved definitions."""
import csv
import io
import json
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, ValidationError
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.qualify import qualify

from backend.analysis_ai import KEY_REQUIRED, Draft, DraftError, configured, generate_draft
from backend.analysis_data import PREPARED, availability, catalog, prepare, schema, unit, unit_key
from backend.analysis_engine import Visual, compile_visual, direct_projection, execute, validate_sql
from backend.silver import store
from src.silver_storage import TABLES

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
Cell = str | int | float | bool | None
TTL = 15 * 60
STARTERS = [
    ("Spending by department", "cost_facts",
     "SELECT reporting_department, SUM(cost_chf) AS recorded_cost_chf, COUNT(cost_chf) AS recorded_rows, "
     "COUNT(*) FILTER (WHERE financial_status IN ('missing_amount', 'missing_fx')) AS missing_cost_rows "
     "FROM cost_facts GROUP BY reporting_department ORDER BY recorded_cost_chf DESC"),
    ("Platform activity versus runtime", "platform_monthly_usage_cost",
     "SELECT resource_id, reporting_month, observed_cluster_hours, active_cluster_hours, node_hours, "
     "recorded_cost_chf, observed_rows, missing_cost_rows FROM platform_monthly_usage_cost ORDER BY resource_id, reporting_month"),
    ("Final AI seat utilization", "ai_subscriptions",
     "SELECT product, reporting_month, SUM(licences_active_30d) AS active_seats, "
     "SUM(licences_purchased) AS purchased_seats, "
     "SUM(licences_active_30d) / NULLIF(SUM(licences_purchased), 0) AS active_share "
     "FROM ai_subscriptions WHERE contract_status = 'Final' GROUP BY product, reporting_month ORDER BY product, reporting_month"),
    ("AI costs by task and model", "ai_usage_with_cost",
     "SELECT task_type, model, SUM(recorded_cost_chf) AS recorded_cost_chf, SUM(requests) AS requests, "
     "COUNT(*) FILTER (WHERE matched_financial_status IN ('missing_amount', 'missing_fx')) AS missing_cost_rows "
     "FROM ai_usage_with_cost GROUP BY task_type, model ORDER BY recorded_cost_chf DESC"),
    ("Server utilization with asset context", "server_metrics_with_assets",
     "SELECT server_id, asset_environment, asset_owner_department, AVG(cpu_avg_pct) AS mean_cpu_pct, "
     "MAX(cpu_max_pct) AS peak_cpu_pct, SUM(uptime_h) AS observed_uptime_hours, "
     "COUNT(*) FILTER (WHERE baseline_boundary_week) AS boundary_weeks FROM server_metrics_with_assets "
     "GROUP BY server_id, asset_environment, asset_owner_department ORDER BY mean_cpu_pct DESC"),
]


class Scope(BaseModel):
    period: Literal["baseline", "full"] = "baseline"
    disposition: Literal["accepted", "review", "duplicate", "quarantined", "all"] = "accepted"
    financial: Literal["eligible", "all"] = "eligible"


class Chart(BaseModel):
    kind: Literal["bar", "line", "scatter", "histogram"] = "bar"
    x: str = ""
    y: str = ""


class Definition(BaseModel):
    version: str = Field(min_length=1, max_length=128)
    dataset: str = Field(min_length=1, max_length=100)
    filters: Scope = Field(default_factory=Scope)
    mode: Literal["visual", "sql"] = "visual"
    visual: Visual = Field(default_factory=Visual)
    sql: str = Field(default="", max_length=30_000)
    chart: Chart = Field(default_factory=Chart)


class SavedInput(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r'\S')
    definition: Definition


class Saved(SavedInput):
    id: str


class DatasetField(BaseModel):
    name: str
    type: str
    unit: str | None
    unit_key: str | None


class Dataset(BaseModel):
    name: str
    purpose: str
    kind: Literal["source", "connected", "prepared"]
    grain: str
    fields: list[DatasetField]
    limitations: list[str]
    unavailable: str | None
    date_context: str
    inputs: list[str]


class Starter(BaseModel):
    name: str
    dataset: str
    sql: str


class Catalog(BaseModel):
    version: str
    baseline_start: str
    baseline_end: str
    defaults: Scope
    datasets: list[Dataset]
    starters: list[Starter]
    ai_configured: bool


class DraftRequest(BaseModel):
    version: str = Field(min_length=1, max_length=128)
    filters: Scope = Field(default_factory=Scope)
    question: str = Field(min_length=1, max_length=2000, pattern=r"\S")


class SQLPreview(BaseModel):
    sql: str


class ResultMetadata(BaseModel):
    id: str
    version: str
    dataset: str
    filters: Scope
    sql: str
    fields: list[DatasetField]
    elapsed_ms: int
    row_count: int
    dataset_rows: int
    coverage: dict[str, int]
    truncated: bool
    requested_limit: int | None
    materialization_limit: int = 10_000
    lineage_field: str | None = None


class ResultPage(BaseModel):
    metadata: ResultMetadata
    offset: int
    limit: int
    rows: list[list[Cell]]


class Runtime:
    def __init__(self, outputs: Path):
        self.file = outputs / "saved_analyses.json"
        self.query_lock = Lock()
        self.lock = Lock()
        self.results = OrderedDict()

    def purge(self):
        now = monotonic()
        while self.results and next(iter(self.results.values()))[0] <= now - TTL:
            self.results.popitem(last=False)

    def add(self, meta, rows):
        with self.lock:
            self.purge()
            self.results[meta.id] = (monotonic(), meta, rows)
            if len(self.results) > 10:
                self.results.popitem(last=False)

    def get(self, key):
        with self.lock:
            self.purge()
            if key not in self.results:
                raise HTTPException(404, detail="Result unavailable or expired. Run the analysis again.")
            _, meta, rows = self.results[key]
            return meta, rows

    def read(self):
        if not self.file.exists():
            return {}
        try:
            return {item.id: item for item in (Saved.model_validate(row)
                    for row in json.loads(self.file.read_text(encoding="utf-8")))}
        except (OSError, ValueError, TypeError, ValidationError) as error:
            raise HTTPException(500, detail="Could not read saved analyses") from error

    def write(self, entries):
        tmp = self.file.with_suffix(".tmp")
        try:
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps([item.model_dump() for item in entries.values()], indent=2), encoding="utf-8")
            tmp.replace(self.file)
        except OSError as error:
            raise HTTPException(500, detail="Could not save analysis definitions") from error


def runtime(request):
    return request.app.state.analysis


@router.get("/catalog", response_model=Catalog)
def get_catalog(request: Request):
    silver, datasets = catalog(request)
    return Catalog(version=silver.version, baseline_start=silver.overview.baseline_start,
                   baseline_end=silver.overview.baseline_end, defaults=Scope(), datasets=datasets,
                   ai_configured=configured(),
                   starters=[Starter(name=name, dataset=dataset, sql=sql) for name, dataset, sql in STARTERS])


def get_definition(request, definition):
    silver = store(request, definition.version)
    if definition.dataset not in TABLES and definition.dataset not in PREPARED:
        raise HTTPException(404, detail="Unknown analysis dataset")
    unavailable = availability(silver, definition.dataset)
    if unavailable:
        raise HTTPException(422, detail=unavailable)
    return silver, schema(silver, definition.dataset)


@router.post("/draft", response_model=Draft)
def draft_query(value: DraftRequest, request: Request):
    store(request, value.version)
    if not configured():
        raise HTTPException(503, detail=KEY_REQUIRED)
    silver, entries = catalog(request)
    datasets = [entry for entry in entries if not entry["unavailable"]]
    available = {entry["name"] for entry in datasets}
    try:
        draft = generate_draft(value.question.strip(), datasets, value.filters.model_dump())
    except DraftError as error:
        raise HTTPException(502, detail=str(error)) from error
    if draft.sql is not None:
        if draft.dataset not in available:
            raise HTTPException(422, detail="AI did not choose an available Silver dataset. Try rephrasing the question.")
        try:
            columns = schema(silver, draft.dataset)
            tree = validate_sql(draft.sql, draft.dataset)
            qualify(tree, dialect="duckdb", schema={draft.dataset: dict.fromkeys(columns, "TEXT")})
        except (ValueError, SqlglotError) as error:
            raise HTTPException(422, detail="The generated SQL did not match the chosen dataset or read-only query rules. Try a narrower question.") from error
    return draft


@router.post("/preview", response_model=SQLPreview)
def preview(definition: Definition, request: Request):
    _, columns = get_definition(request, definition)
    try:
        sql = compile_visual(definition.dataset, columns, definition.visual)
        validate_sql(sql, definition.dataset)
        return SQLPreview(sql=sql)
    except (ValueError, ArithmeticError, SqlglotError) as error:
        raise HTTPException(422, detail=str(error)) from error


@router.post("/query", response_model=ResultPage)
def run(definition: Definition, request: Request):
    silver, columns = get_definition(request, definition)
    state = runtime(request)
    if not state.query_lock.acquire(blocking=False):
        raise HTTPException(429, detail="A Silver query is already running. Try again when it finishes.")
    try:
        name = definition.dataset
        sql = compile_visual(name, columns, definition.visual) if definition.mode == "visual" else definition.sql
        tree = validate_sql(sql, name)
        normalized = tree.sql(dialect="duckdb", comments=False)
        rows, coverage = prepare(silver, name, definition.filters)
        fields, result, truncated, elapsed = execute(name, columns, rows, normalized)
        projected = direct_projection(tree, columns)
        lineage_field = ("record_id" if projected.get("record_id") == "record_id"
                         and not tree.args.get("group") and not any(tree.find_all(exp.AggFunc))
                         and any(row.get("record_id") in silver.records for row in rows) else None)
        metrics = {metric.name: metric for metric in definition.visual.metrics} if definition.mode == "visual" else {}
        aggregate_origins = {}
        source = tree.args.get("from_")
        if source and isinstance(source.this, exp.Table) and not tree.args.get("with_"):
            for item in tree.expressions:
                value = item.this if isinstance(item, exp.Alias) else item
                if isinstance(value, (exp.Sum, exp.Min, exp.Max, exp.Avg, exp.Median)) and isinstance(value.this, exp.Column):
                    origin = value.this.name.lower()
                    if origin in columns and not unit_key(name, origin, columns):
                        aggregate_origins[item.output_name] = origin
        metadata_fields = []
        for field, kind in fields:
            origin = projected.get(field) or aggregate_origins.get(field)
            metric = metrics.get(field)
            if metric and metric.op in {"min", "max", "sum", "mean", "median"}:
                origin = metric.field
            derived_unit = "count" if metric and metric.op in {"rows", "count", "distinct"} else "Unverified"
            metadata_fields.append(DatasetField(name=field, type=kind,
                                                unit=unit(name, origin) if origin else derived_unit,
                                                unit_key=unit_key(name, origin, columns) if origin else None))
        limit = tree.args.get("limit")
        requested_limit = (limit.expression.to_py() if limit and isinstance(limit.expression, exp.Literal)
                           and limit.expression.is_int else None)
        meta = ResultMetadata(id=uuid4().hex, version=silver.version, dataset=name, filters=definition.filters,
                              sql=sql, fields=metadata_fields, elapsed_ms=elapsed, row_count=len(result),
                              dataset_rows=len(rows), coverage=coverage, truncated=truncated,
                              requested_limit=requested_limit, lineage_field=lineage_field)
        state.add(meta, result)
        return ResultPage(metadata=meta, offset=0, limit=100, rows=result[:100])
    except (ValueError, ArithmeticError, SqlglotError) as error:
        raise HTTPException(422, detail=str(error)) from error
    except TimeoutError as error:
        raise HTTPException(408, detail=str(error)) from error
    finally:
        state.query_lock.release()


@router.get("/results/{key}", response_model=ResultPage)
def page(key: str, request: Request, offset: int = Query(0, ge=0),
         limit: int = Query(100, ge=1, le=1000)):
    meta, rows = runtime(request).get(key)
    return ResultPage(metadata=meta, offset=offset, limit=limit, rows=rows[offset:offset + limit])


@router.get("/results/{key}/metadata", response_model=ResultMetadata)
def export_metadata(key: str, request: Request):
    meta, _ = runtime(request).get(key)
    return Response(meta.model_dump_json(indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="analysis-{meta.id}.json"'})


@router.get("/results/{key}/csv", response_class=Response)
def export_csv(key: str, request: Request):
    meta, rows = runtime(request).get(key)
    content = io.StringIO(newline="")
    writer = csv.writer(content)
    writer.writerow([field.name for field in meta.fields])
    writer.writerows(rows)
    return Response(content.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="analysis-{meta.id}.csv"'})


@router.get("/saved", response_model=list[Saved])
def saved(request: Request):
    state = runtime(request)
    with state.lock:
        return list(state.read().values())


def change_saved(request, key, value, create=False):
    state = runtime(request)
    with state.lock:
        entries = state.read()
        if not create and key not in entries:
            raise HTTPException(404, detail="Unknown saved analysis")
        if value is None:
            del entries[key]
        else:
            entries[key] = Saved(id=key, name=value.name.strip(), definition=value.definition)
        state.write(entries)
        return entries.get(key)


@router.post("/saved", response_model=Saved, status_code=201)
def save(value: SavedInput, request: Request):
    return change_saved(request, uuid4().hex, value, create=True)


@router.put("/saved/{key}", response_model=Saved)
def update(key: str, value: SavedInput, request: Request):
    return change_saved(request, key, value)


@router.delete("/saved/{key}", status_code=204)
def delete(key: str, request: Request):
    change_saved(request, key, None)
    return Response(status_code=204)
