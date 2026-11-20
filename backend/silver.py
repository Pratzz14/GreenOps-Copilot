"""Read-only, startup-loaded Silver exploration API."""
import csv
from sys import intern
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from src.silver_rules import FREE_TEXT
from src.normalize import AUDIT_FIELDS
from src.profile import END, START, read_csv
from src.reconciliation import FILES
from src.silver_profiles import field_type
from src.silver_storage import SOURCE_TABLES, TABLES, pointer, silver_directory, validate
from src.source_specs import SPECS

Scope = Literal['full', 'baseline']
Status = Literal['accepted', 'review', 'duplicate', 'quarantined', 'all']
Cell = str | int | bool | None
Row = dict[str, Cell]
router = APIRouter(prefix='/api/v1/silver', tags=['silver'])

PURPOSES = {
    'cost_facts': 'Provider charges, gateway costs and monthly contract amounts',
    'usage_facts': 'Platform, server and AI measurements',
    'assets': 'Inventory snapshot and ownership attributes',
    'contracts': 'Monthly contract versions including Draft and Final',
    'ownership': 'Documented resource and cost-center associations',
    'resource_relationships': 'Billing-to-asset evidence and unresolved pools',
}
PROFILE_COUNTS = {'valid', 'missing', 'not_applicable', 'optional_blank', 'invalid',
                  'bronze_rows', 'bronze_missing', 'matched_bronze_missing', 'silver_rows', 'count'}


class Versioned(BaseModel):
    version: str


class CatalogEntry(BaseModel):
    table: str
    purpose: str
    total: int
    accepted: int
    issue_count: int
    limitations: list[str]
    transformations: dict[str, int]


class SilverOverview(Versioned):
    snapshot_id: str
    status: Literal['Ready', 'Ready with unresolved issues']
    tables: list[CatalogEntry]
    accepted: int
    duplicates: int
    review: int
    quarantined: int
    issues: int
    issue_codes: list[str]
    field_changes: int
    rules: dict[str, int]
    baseline_start: str
    baseline_end: str
    recorded_cost_chf: str
    coverage_status: str


class Page(Versioned):
    total: int
    offset: int
    limit: int
    items: list[Row]


class TablePage(Page):
    table: str
    columns: dict[str, str]


class TableProfile(Versioned):
    table: str
    scope: Scope
    items: list[Row]


class Lineage(Versioned):
    record: Row
    changes: list[Row]
    issues: list[Row]


def typed(name, row):
    result = {}
    for field, value in row.items():
        kind = field_type(name, field)
        if not value and not (name in TABLES and field in FREE_TEXT):
            result[field] = None
        elif (kind == 'integer' or name == 'profiles' and field in PROFILE_COUNTS
              or name == 'reconciliation_report' and field in {
                  'record_count', 'included', 'missing_amount', 'missing_fx', 'draft', 'duplicate',
                  'outside_baseline', 'review', 'quarantined',
              }):
            result[field] = int(value)
        elif kind == 'boolean' or field == 'agrees_with_total':
            if value not in {'True', 'False'}:
                raise ValueError(f'Invalid boolean field: {field}')
            result[field] = value == 'True'
        elif kind == 'decimal':
            if not Decimal(value).is_finite():
                raise ValueError(f'Invalid decimal field: {field}')
            result[field] = value
        else:
            result[field] = value
    return result


class Silver:
    def __init__(self, directory, version, snapshot):
        self.version = version
        self.rows = {}
        self.columns = {}
        for name in FILES:
            if name == 'transformation_log':
                continue
            columns, rows = read_csv(directory / f'{name}.csv')
            self.columns[name] = {field: field_type(name, field) for field in columns}
            self.rows[name] = [typed(name, row) for row in rows]
        self.profiles = defaultdict(list)
        self.audit = defaultdict(list)
        self.issues = defaultdict(list)
        self.records = {}
        for item in self.rows['profiles']:
            self.profiles[item['table'], item['scope']].append(item)
        issues_by_file = defaultdict(Counter)
        for item in self.rows['unresolved_issues']:
            self.issues[item['record_id']].append(item)
            issues_by_file[item['source_file']][item['code']] += 1
        catalog = []
        audit_counts = defaultdict(Counter)
        status = Counter()
        for name in TABLES:
            rows = self.rows[name]
            counts = Counter(row.get('record_status', 'accepted') for row in rows)
            findings = issues_by_file[f'{name}.csv']
            if name in SOURCE_TABLES:
                status.update(counts)
                for row in rows:
                    if row['record_id'] in self.records or row['snapshot_id'] != snapshot:
                        raise ValueError('Invalid Silver record identity')
                    self.records[row['record_id']] = row
            if name not in SOURCE_TABLES:
                record_ids = {row.get('record_id') for row in rows}
                findings = Counter(item['code'] for key in record_ids if key for item in self.issues.get(key, ()))
                if name == 'resource_relationships':
                    findings = Counter(item['code'] for item in self.rows['unresolved_issues']
                                       if item['code'] in {'unverified_asset_relationship', 'unresolved_billing_pool'})
            catalog.append(dict(table=name, purpose=PURPOSES.get(name) or SPECS[f'{name}.csv'].role,
                                        total=len(rows), accepted=counts['accepted'], issue_count=sum(findings.values()),
                                        limitations=[f'{count:,} {code.replace("_", " ")}' for code, count in findings.most_common()]))
        rules, changes = self.load_audit(directory / 'transformation_log.csv', audit_counts)
        catalog = [CatalogEntry(**item, transformations=dict(audit_counts[f"{item['table']}.csv"]))
                   for item in catalog]
        baseline, = self.rows['cost_baseline']
        issues = self.rows['unresolved_issues']
        self.overview = SilverOverview(
            version=version, snapshot_id=snapshot, status='Ready with unresolved issues' if issues else 'Ready',
            tables=catalog, accepted=status['accepted'], duplicates=status['duplicate'], review=status['review'],
            quarantined=status['quarantined'], issues=len(issues),
            issue_codes=sorted({row['code'] for row in issues}), rules=dict(rules),
            field_changes=changes,
            baseline_start=START.isoformat(), baseline_end=END.isoformat(),
            recorded_cost_chf=baseline['recorded_cost_chf'], coverage_status=baseline['coverage_status'])


    def load_audit(self, path, audit_counts):
        rules = Counter()
        changes = 0
        with path.open(encoding='utf-8', newline='') as handle:
            reader = csv.reader(handle, strict=True)
            if tuple(next(reader, ())) != AUDIT_FIELDS:
                raise ValueError('Invalid Silver audit schema')
            for key, source, index, field, original, cleaned, rule, reason, evidence in reader:
                record = self.records.get(key)
                if record is None or source != record['source_file'] or int(index) != record['source_row']:
                    raise ValueError('Audit entry has no matching Silver source row')
                rules[rule] += 1
                audit_counts[source][rule] += 1
                changes += original != cleaned
                self.audit[record['record_id']].append((
                    intern(field), original or None, cleaned or None, intern(rule),
                    intern(reason), evidence or None,
                ))
        return rules, changes

    def record_changes(self, record):
        return [dict(record_id=record['record_id'], source_file=record['source_file'],
                     source_row=record['source_row'], **dict(zip(AUDIT_FIELDS[3:], entry, strict=True)))
                for entry in self.audit.get(record['record_id'], ())]


def load_silver(out: Path, snapshot: str | None):
    try:
        version = pointer(out, 'current')
        directory = silver_directory(out) / version
        bronze, _ = validate(directory, version, FILES, snapshot)
        return Silver(directory, version, bronze), None
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, csv.Error) as error:
        return None, f'{error}. Run normalization and reconciliation, then restart the API.'


def store(request, version=None):
    silver = request.app.state.silver
    if silver is None:
        raise HTTPException(503, detail={'message': request.app.state.silver_error})
    if version and version != silver.version:
        raise HTTPException(409, detail={'version': silver.version, 'message': 'Silver version changed. Reload the overview.'})
    return silver


def require_table(table, allowed=TABLES):
    if table not in allowed:
        raise HTTPException(404, detail='Unknown Silver table')


@router.get('', response_model=SilverOverview)
def overview(request: Request):
    return store(request).overview


@router.get('/tables/{table}/profile', response_model=TableProfile)
def table_profile(table: str, request: Request, scope: Scope = 'full', version: str | None = None):
    silver = store(request, version)
    require_table(table, SOURCE_TABLES)
    return TableProfile(version=silver.version, table=table, scope=scope, items=silver.profiles[table, scope])


@router.get('/tables/{table}/rows', response_model=TablePage)
def table_rows(table: str, request: Request, scope: Scope = 'full', status: Status = 'accepted',
               offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), version: str | None = None):
    silver = store(request, version)
    require_table(table)
    rows = [row for row in silver.rows[table] if
            (status == 'all' or row.get('record_status', 'accepted') == status) and
            (scope == 'full' or 'baseline_overlap' not in row or row.get('baseline_overlap') or row.get('baseline_context'))]
    return TablePage(version=silver.version, table=table, columns=silver.columns[table], total=len(rows),
                     offset=offset, limit=limit, items=rows[offset:offset + limit])


@router.get('/records/{record_id}', response_model=Lineage)
def record_lineage(record_id: str, request: Request, version: str | None = None):
    silver = store(request, version)
    if record_id not in silver.records:
        raise HTTPException(404, detail='Unknown Silver record')
    record = silver.records[record_id]
    return Lineage(version=silver.version, record=record,
                   changes=silver.record_changes(record), issues=silver.issues.get(record_id, []))


@router.get('/issues', response_model=Page)
def unresolved(request: Request, source: str | None = None, code: str | None = None,
               offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), version: str | None = None):
    silver = store(request, version)
    if source:
        require_table(source, SOURCE_TABLES)
    if code and code not in silver.overview.issue_codes:
        raise HTTPException(422, detail='Unknown Silver issue code')
    rows = [row for row in silver.rows['unresolved_issues'] if
            (not source or row['source_file'] == f'{source}.csv') and (not code or row['code'] == code)]
    return Page(version=silver.version, total=len(rows), offset=offset, limit=limit, items=rows[offset:offset + limit])


@router.get('/reconciliation', response_model=Page)
def financial(request: Request, dimension: Literal['total', 'source_file', 'provider', 'reporting_month',
                                                     'reporting_department', 'currency'] = 'source_file',
              offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), version: str | None = None):
    silver = store(request, version)
    rows = [row for row in silver.rows['reconciliation_report'] if row['dimension'] == dimension]
    return Page(version=silver.version, total=len(rows), offset=offset, limit=limit, items=rows[offset:offset + limit])
