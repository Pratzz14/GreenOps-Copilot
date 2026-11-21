"""Typed read-only Gold results shared with the generated frontend contract."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from backend.schemas import Contract, Overview, RunIdentity

Scenario = Literal["low", "mid", "high"]
Horizon = Literal["first_year", "steady_state"]
Coverage = Literal["complete", "partial", "unknown"]
Group = Literal["department", "tool", "provider", "location", "subject"]


class GoldRun(RunIdentity):
    snapshot_id: str
    decision_as_of: date
    conditional_package_id: str | None


class GoldOverview(Overview):
    imputed_cost_chf: Decimal | None = None
    recovered_cost_chf: Decimal | None = None
    swiss_operating_kg_co2e: Decimal | None = None
    cost_coverage: Coverage
    energy_coverage: Coverage
    carbon_coverage: Coverage
    included_rows: int
    missing_amount_rows: int
    missing_fx_rows: int
    review_rows: int
    evidence_set_id: str


class GoldBreakdown(Contract):
    report_month: date | None
    driver: str
    recorded_cost_chf: Decimal | None
    imputed_cost_chf: Decimal | None = None
    recovered_cost_chf: Decimal | None = None
    swiss_operating_kg_co2e: Decimal | None = None
    estimated_kwh: Decimal | None
    estimated_location_kg: Decimal | None
    unresolved_cost_rows: int
    incomplete_energy_buckets: int
    incomplete_carbon_buckets: int
    spend_rank: int | None
    emissions_rank: int | None


class GoldFinding(Contract):
    finding_id: str
    subject_name: str
    category: str
    observed_start: date | None
    observed_end_exclusive: date | None
    observed_fact: str
    waste_hypothesis: str
    verification_status: str
    confidence: str
    evidence_set_id: str


class GoldFactor(Contract):
    factor_id: str
    factor_name: str
    submission_parameter: str | None
    location: str | None
    value_low: Decimal | None
    value_mid: Decimal | None
    value_high: Decimal | None
    value_text: str | None
    unit: str
    source_reference: str
    source_date: date | None
    definition_and_rationale: str


class GoldScenario(Contract):
    scenario: Scenario
    horizon: Horizon
    estimate_status: str
    net_chf: Decimal | None
    savings_kwh: Decimal | None
    savings_location_kg: Decimal | None
    evidence_set_id: str


class GoldMeasure(Contract):
    measure_id: str
    subject_name: str
    description: str
    proposed_change: str
    earliest_effective_date: date | None
    notice_deadline: date | None
    effort_person_days: Decimal | None
    one_time_cash_chf: Decimal | None
    safety_status: Literal["eligible", "human_review", "blocked"]
    responsible_role: str | None
    risks_and_exceptions: str
    evidence_set_id: str
    estimates: list[GoldScenario]


class GoldProtection(Contract):
    subject_name: str
    rule_key: str
    action_scope: str
    starts_at: datetime | None
    ends_at: datetime | None
    decision: Literal["blocked", "human_review", "conditions_apply"]
    responsible_role: str | None
    reason: str
    evidence_set_id: str


class GoldSafety(Contract):
    decisions: list[GoldMeasure]
    protections: list[GoldProtection]


class GoldMember(Contract):
    measure_id: str
    description: str
    scenario: Scenario
    horizon: Horizon
    credited_cost_chf: Decimal
    credited_energy_kwh: Decimal
    credited_location_kg: Decimal
    credited_implementation_chf: Decimal
    evidence_set_id: str


class GoldScore(Contract):
    scenario: Scenario
    horizon: Horizon
    evaluation_start: date | None
    evaluation_end_exclusive: date | None
    target_status: Literal["conditional", "unassessed", "meets_targets", "misses_targets"]
    meets_all_three_scenarios: bool | None
    baseline_cost_chf: Decimal | None
    baseline_energy_kwh: Decimal | None
    baseline_location_kg: Decimal | None
    after_cost_chf: Decimal | None
    after_energy_kwh: Decimal | None
    after_location_kg: Decimal | None
    net_savings_chf: Decimal
    savings_energy_kwh: Decimal
    savings_location_kg: Decimal
    implementation_chf: Decimal
    cost_reduction: Decimal | None
    carbon_reduction: Decimal | None
    cost_margin_chf: Decimal | None
    carbon_margin_kg: Decimal | None
    budget_remaining_chf: Decimal


class GoldPackage(Contract):
    run_id: str
    package_id: str
    package_kind: Literal["automatic", "conditional"]
    selection_status: Literal["pending", "provisional", "feasible", "infeasible"]
    candidate_set_note: str
    evidence_set_id: str
    emissions_basis: Literal["CO2", "CO2e"]
    cost_target: Decimal
    carbon_target: Decimal
    implementation_cap_chf: Decimal
    scores: list[GoldScore]
    members: list[GoldMember]


class EvidenceItem(Contract):
    evidence_type: str
    source_file: str | None
    source_row: int | None
    source_record_id: str | None
    detail: str
    factor_id: str | None
    factor_name: str | None
    source_reference: str | None


class EvidencePage(Contract):
    run_id: str
    evidence_set_id: str
    total: int
    offset: int
    items: list[EvidenceItem]


class GoldTableInfo(Contract):
    name: str
    row_count: int


class GoldTableCatalog(Contract):
    run_id: str
    tables: list[GoldTableInfo]


class GoldTableColumn(Contract):
    name: str
    type: str
    primary_key: bool


class GoldTablePage(Contract):
    run_id: str
    table: str
    row_count: int
    offset: int
    limit: int
    columns: list[GoldTableColumn]
    items: list[dict[str, str | None]]
