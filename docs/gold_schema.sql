-- DuckDB reference schema for the proposed Gold contract.
-- Run in a new or disposable DuckDB database. The schema creates empty tables.
CREATE SCHEMA gold;

CREATE TABLE gold.analysis_run (
    run_id VARCHAR PRIMARY KEY,
    snapshot_id VARCHAR NOT NULL,
    silver_version VARCHAR NOT NULL,
    calculation_version VARCHAR NOT NULL,
    baseline_start DATE NOT NULL,
    baseline_end_exclusive DATE NOT NULL,
    decision_as_of DATE NOT NULL,
    schedule_timezone VARCHAR NOT NULL,
    emissions_basis VARCHAR NOT NULL CHECK (emissions_basis IN ('CO2', 'CO2e')),
    cost_coverage VARCHAR NOT NULL CHECK (cost_coverage IN ('complete', 'partial', 'unknown')),
    energy_coverage VARCHAR NOT NULL CHECK (energy_coverage IN ('complete', 'partial', 'unknown')),
    carbon_coverage VARCHAR NOT NULL CHECK (carbon_coverage IN ('complete', 'partial', 'unknown')),
    cost_reduction_target DECIMAL(8, 6) NOT NULL,
    carbon_reduction_target DECIMAL(8, 6) NOT NULL,
    implementation_cap_chf DECIMAL(18, 2) NOT NULL,
    day_rate_chf DECIMAL(18, 2) NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    CHECK (baseline_start < baseline_end_exclusive)
);

CREATE TABLE gold.subject (
    run_id VARCHAR NOT NULL REFERENCES gold.analysis_run(run_id),
    subject_id VARCHAR NOT NULL,
    subject_type VARCHAR NOT NULL,
    subject_name VARCHAR NOT NULL,
    environment VARCHAR,
    criticality VARCHAR,
    responsible_role VARCHAR,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, subject_id)
);

CREATE TABLE gold.cost_monthly (
    run_id VARCHAR NOT NULL,
    report_month DATE NOT NULL,
    subject_id VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    tool VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    cost_stream VARCHAR NOT NULL,
    recorded_cost_chf DECIMAL(28, 12),
    imputed_cost_chf DECIMAL(28, 12),
    recovered_cost_chf DECIMAL(28, 12),
    included_rows BIGINT NOT NULL,
    missing_amount_rows BIGINT NOT NULL,
    missing_fx_rows BIGINT NOT NULL,
    review_rows BIGINT NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, report_month, subject_id, provider, department, tool, location, cost_stream),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id)
);

CREATE TABLE gold.impact_monthly (
    run_id VARCHAR NOT NULL,
    report_month DATE NOT NULL,
    subject_id VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    tool VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    boundary_id VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL CHECK (scenario IN ('low', 'mid', 'high')),
    energy_kwh DECIMAL(28, 12),
    location_kg DECIMAL(28, 12),
    swiss_operating_kg_co2e DECIMAL(28, 12),
    reporting_kg_co2e DECIMAL(28, 12),
    planning_kwh DECIMAL(28, 12),
    planning_kg_co2e DECIMAL(28, 12),
    activity_quantity DECIMAL(28, 12),
    activity_unit VARCHAR,
    energy_gap_reason VARCHAR,
    carbon_gap_reason VARCHAR,
    energy_coverage VARCHAR NOT NULL CHECK (energy_coverage IN ('complete', 'partial', 'unknown')),
    carbon_coverage VARCHAR NOT NULL CHECK (carbon_coverage IN ('complete', 'partial', 'unknown')),
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, report_month, subject_id, provider, department, tool, location, boundary_id, scenario),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id)
);

CREATE TABLE gold.factor (
    run_id VARCHAR NOT NULL REFERENCES gold.analysis_run(run_id),
    factor_id VARCHAR NOT NULL,
    submission_parameter VARCHAR,
    factor_name VARCHAR NOT NULL,
    location VARCHAR,
    valid_from DATE,
    valid_to_exclusive DATE,
    value_low DECIMAL(28, 12),
    value_mid DECIMAL(28, 12),
    value_high DECIMAL(28, 12),
    value_text VARCHAR,
    unit VARCHAR NOT NULL,
    source_reference VARCHAR NOT NULL,
    source_date DATE,
    definition_and_rationale VARCHAR NOT NULL,
    PRIMARY KEY (run_id, factor_id),
    UNIQUE (run_id, submission_parameter)
);

CREATE TABLE gold.licence_monthly (
    run_id VARCHAR NOT NULL,
    report_month DATE NOT NULL,
    contract_key VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    product_name VARCHAR NOT NULL,
    licence_type VARCHAR NOT NULL CHECK (licence_type IN ('ai_subscription', 'saas')),
    provider VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    purchased_seats INTEGER,
    active_seats INTEGER,
    monthly_price_per_seat_chf DECIMAL(28, 12),
    billing_cycle VARCHAR,
    contract_end DATE,
    notice_period_days INTEGER,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, report_month, contract_key),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id)
);

CREATE TABLE gold.finding (
    run_id VARCHAR NOT NULL,
    finding_id VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    observed_start DATE,
    observed_end_exclusive DATE,
    observed_fact VARCHAR NOT NULL,
    waste_hypothesis VARCHAR NOT NULL,
    verification_status VARCHAR NOT NULL,
    confidence VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, finding_id),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id)
);

CREATE TABLE gold.protection_window (
    run_id VARCHAR NOT NULL,
    protection_id VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    rule_key VARCHAR NOT NULL,
    action_scope VARCHAR NOT NULL,
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    decision VARCHAR NOT NULL CHECK (decision IN ('blocked', 'human_review', 'conditions_apply')),
    responsible_role VARCHAR,
    reason VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, protection_id),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id),
    CHECK (starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at)
);

CREATE TABLE gold.measure (
    run_id VARCHAR NOT NULL,
    measure_id VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    finding_id VARCHAR,
    description VARCHAR NOT NULL,
    proposed_change VARCHAR NOT NULL,
    earliest_effective_date DATE,
    notice_deadline DATE,
    effort_person_days DECIMAL(12, 4),
    one_time_cash_chf DECIMAL(18, 2),
    safety_status VARCHAR NOT NULL CHECK (safety_status IN ('eligible', 'human_review', 'blocked')),
    responsible_role VARCHAR,
    risks_and_exceptions VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, measure_id),
    FOREIGN KEY (run_id, subject_id) REFERENCES gold.subject(run_id, subject_id),
    FOREIGN KEY (run_id, finding_id) REFERENCES gold.finding(run_id, finding_id)
);

CREATE TABLE gold.measure_scenario (
    run_id VARCHAR NOT NULL,
    measure_id VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL CHECK (scenario IN ('low', 'mid', 'high')),
    horizon VARCHAR NOT NULL CHECK (horizon IN ('first_year', 'steady_state')),
    gross_avoided_chf DECIMAL(28, 12),
    new_recurring_chf DECIMAL(28, 12),
    before_energy_kwh DECIMAL(28, 12),
    after_energy_kwh DECIMAL(28, 12),
    before_location_kg DECIMAL(28, 12),
    after_location_kg DECIMAL(28, 12),
    estimate_status VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, measure_id, scenario, horizon),
    FOREIGN KEY (run_id, measure_id) REFERENCES gold.measure(run_id, measure_id)
);

CREATE TABLE gold.measure_constraint (
    run_id VARCHAR NOT NULL,
    measure_id VARCHAR NOT NULL,
    related_measure_id VARCHAR NOT NULL,
    constraint_type VARCHAR NOT NULL CHECK (constraint_type IN ('requires', 'excludes', 'overlaps')),
    resolution_note VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, measure_id, related_measure_id, constraint_type),
    FOREIGN KEY (run_id, measure_id) REFERENCES gold.measure(run_id, measure_id),
    FOREIGN KEY (run_id, related_measure_id) REFERENCES gold.measure(run_id, measure_id),
    CHECK (measure_id <> related_measure_id)
);

CREATE TABLE gold.package_result (
    run_id VARCHAR NOT NULL REFERENCES gold.analysis_run(run_id),
    package_id VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL CHECK (scenario IN ('low', 'mid', 'high')),
    horizon VARCHAR NOT NULL CHECK (horizon IN ('first_year', 'steady_state')),
    package_kind VARCHAR NOT NULL CHECK (package_kind IN ('automatic', 'conditional')),
    evaluation_status VARCHAR NOT NULL CHECK (evaluation_status IN ('pending', 'provisional', 'evaluated')),
    selection_status VARCHAR NOT NULL CHECK (selection_status IN ('pending', 'provisional', 'feasible', 'infeasible')),
    candidate_set_note VARCHAR NOT NULL,
    evaluation_start DATE,
    evaluation_end_exclusive DATE,
    baseline_cost_chf DECIMAL(28, 12),
    baseline_energy_kwh DECIMAL(28, 12),
    baseline_location_kg DECIMAL(28, 12),
    net_savings_chf DECIMAL(28, 12),
    savings_energy_kwh DECIMAL(28, 12),
    savings_location_kg DECIMAL(28, 12),
    implementation_chf DECIMAL(28, 12),
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, package_id, scenario, horizon),
    CHECK (evaluation_start IS NULL OR evaluation_end_exclusive > evaluation_start)
);

CREATE TABLE gold.package_member (
    run_id VARCHAR NOT NULL,
    package_id VARCHAR NOT NULL,
    scenario VARCHAR NOT NULL,
    horizon VARCHAR NOT NULL,
    measure_id VARCHAR NOT NULL,
    credited_cost_chf DECIMAL(28, 12),
    credited_energy_kwh DECIMAL(28, 12),
    credited_location_kg DECIMAL(28, 12),
    credited_implementation_chf DECIMAL(28, 12),
    allocation_note VARCHAR NOT NULL,
    evidence_set_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, package_id, scenario, horizon, measure_id),
    FOREIGN KEY (run_id, package_id, scenario, horizon)
        REFERENCES gold.package_result(run_id, package_id, scenario, horizon),
    FOREIGN KEY (run_id, measure_id) REFERENCES gold.measure(run_id, measure_id)
);

CREATE TABLE gold.evidence (
    run_id VARCHAR NOT NULL REFERENCES gold.analysis_run(run_id),
    evidence_set_id VARCHAR NOT NULL,
    evidence_no BIGINT NOT NULL,
    evidence_type VARCHAR NOT NULL,
    source_file VARCHAR,
    source_row BIGINT,
    source_record_id VARCHAR,
    factor_id VARCHAR,
    detail VARCHAR NOT NULL,
    PRIMARY KEY (run_id, evidence_set_id, evidence_no),
    FOREIGN KEY (run_id, factor_id) REFERENCES gold.factor(run_id, factor_id)
);
