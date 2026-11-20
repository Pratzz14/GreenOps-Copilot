"""Typed profiling artifacts and compact API payloads."""
from typing import Literal
from pydantic import Field
from backend.schemas import Contract

Scope = Literal['full', 'baseline']
Scalar = str | float | None

class Bin(Contract):
    label: str
    count: int

class Distribution(Contract):
    label: str
    count: int
    minimum: float
    maximum: float
    mean: float
    median: float
    histogram: list[Bin]

class ColumnProfile(Contract):
    name: str
    expected_type: str
    observed_type: str
    blanks: int
    expected_blank: int
    missing: int
    invalid: int
    distinct: int
    distributions: list[Distribution]
    applicable_rows: int
    minimum: Scalar
    maximum: Scalar
    mean: float | None
    median: float | None
    histogram: list[Bin]

class Evidence(Contract):
    source_row: int
    values: dict[str, str]

class QualityIssue(Contract):
    code: str
    severity: Literal['warning', 'error']
    source: str
    columns: list[str]
    count: int
    rows: list[int]
    message: str
    examples: list[Evidence]

class Coverage(Contract):
    minimum: str
    maximum: str
    distinct_periods: int
    cadence: str

class Gap(Contract):
    entity: str
    internal_gaps: list[str]
    baseline_absent_periods: list[str]
    certainty: str

class JoinAssessment(Contract):
    label: str
    target: str
    columns: list[str]
    cardinality: str
    matched: int
    unmatched: int
    blank_keys: int
    ambiguous: int
    unmatched_rows: list[int]
    blank_rows: list[int]
    ambiguous_rows: list[int]
    ownership_conflict_rows: list[int]
    missing_department_rows: list[int]
    notes: str

class ProjectVariants(Contract):
    column: str
    proposed: str
    variants: dict[str,int]

class TagProfile(Contract):
    empty_objects: int
    absent_keys: dict[str,int]
    blank_values: dict[str,int]
    invalid_rows: list[int]

class AmountProfile(Contract):
    currency: str
    charge_type: str
    rows: int
    missing: int
    negative_count: int
    negative_rows: list[int]

class MonthRows(Contract):
    month: str
    rows: int

class Conflict(Contract):
    key: list[str]
    rows: list[int]

class View(Contract):
    rows: int
    column_count: int
    columns: list[ColumnProfile]
    issues: list[QualityIssue]
    issue_counts: dict[str,int]
    missing_cells: int
    blank_cells: int
    cell_count: int
    missing_percent: float | None
    candidate_key: list[str]
    unique_key_count: int
    key_collision_groups: list[list[int]]
    exact_duplicate_groups: list[list[int]]
    duplicate_excess: int
    contract_conflicts: list[Conflict]
    categories: dict[str,dict[str,int]]
    project_variants: list[ProjectVariants]
    azure_tags: TagProfile | None
    amounts: list[AmountProfile]
    date_coverage: Coverage | None
    gaps: list[Gap]
    boundary_rows: list[int]
    monthly_rows: list[MonthRows]
    scope_note: str
    joins: list[JoinAssessment]

class Mapping(Contract):
    source: str
    rule: str

class Source(Contract):
    name: str
    role: str
    cadence: str
    sha256: str
    canonical_mapping: dict[str,Mapping]
    views: dict[Scope,View]

class InputHash(Contract):
    name: str
    sha256: str

class Period(Contract):
    start: str
    end: str

class Parameter(Contract):
    parameter: str
    unit: str
    status: str

class Template(Contract):
    name: str
    columns: list[str]
    rows: int
    parameters: list[Parameter]
    status: str

class Report(Contract):
    schema_version: Literal[2]
    profiling_version: Literal['2.0']
    snapshot_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    report_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    inputs: list[InputHash]
    baseline: Period
    sources: list[Source]
    templates: list[Template]
    limitations: list[str]

class SourceSummary(Contract):
    name: str
    role: str
    cadence: str
    rows: int
    column_count: int
    missing_percent: float | None
    missing_cells: int
    duplicate_excess: int
    issue_counts: dict[str,int]
    date_coverage: Coverage | None
    gap_count: int

class QualityOverview(Contract):
    report_id: str
    snapshot_id: str
    baseline: Period
    scope: Scope
    sources: list[SourceSummary]
    limitations: list[str]

class SourceDetail(Contract):
    report_id: str
    name: str
    role: str
    cadence: str
    scope: Scope
    profile: View
    canonical_mapping: dict[str,Mapping]

class IssuePage(Contract):
    report_id: str
    total: int
    offset: int
    limit: int
    items: list[QualityIssue]
