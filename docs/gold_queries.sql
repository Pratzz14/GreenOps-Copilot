-- Read-only DuckDB queries for the contract in gold_schema.sql.
-- Set the session variables listed in GOLD_LAYER.md. Run statements individually.

-- Q01. Annual executive baseline with separately reported coverage.
WITH costs AS (
    SELECT sum(recorded_cost_chf) AS recorded_cost_chf, sum(imputed_cost_chf) AS imputed_cost_chf,
           sum(recovered_cost_chf) AS recovered_cost_chf,
           sum(included_rows) AS included_rows, sum(missing_amount_rows) AS missing_amount_rows,
           sum(missing_fx_rows) AS missing_fx_rows, sum(review_rows) AS review_rows
    FROM gold.cost_monthly
    WHERE run_id = getvariable('gold_run_id')
), impact AS (
    SELECT sum(energy_kwh) AS estimated_kwh, sum(location_kg) AS estimated_location_kg,
           sum(swiss_operating_kg_co2e) AS swiss_operating_kg_co2e,
           sum(reporting_kg_co2e) AS reporting_kg_co2e,
           CASE WHEN count(reporting_kg_co2e) = 0 THEN 'unknown'
                WHEN bool_and(reporting_kg_co2e IS NOT NULL AND energy_coverage = 'complete') THEN 'complete'
                ELSE 'partial' END AS reporting_carbon_coverage
    FROM gold.impact_monthly
    WHERE run_id = getvariable('gold_run_id') AND scenario = getvariable('gold_scenario')
)
SELECT r.run_id, r.snapshot_id, r.silver_version, r.baseline_start, r.baseline_end_exclusive,
       getvariable('gold_scenario') AS scenario, r.emissions_basis,
       c.*, i.*, r.cost_coverage, r.energy_coverage, r.carbon_coverage
FROM gold.analysis_run AS r CROSS JOIN costs AS c CROSS JOIN impact AS i
WHERE r.run_id = getvariable('gold_run_id');

-- Q02. Monthly trends and independent rankings of spending and emissions drivers.
-- Set gold_group_by to provider, department, tool, location, or subject.
WITH metrics AS (
    SELECT report_month, subject_id, provider, department, tool, location,
           recorded_cost_chf, imputed_cost_chf, recovered_cost_chf,
           NULL AS energy_kwh, NULL AS location_kg, NULL AS swiss_operating_kg_co2e, NULL AS reporting_kg_co2e,
           missing_amount_rows + missing_fx_rows + review_rows AS unresolved_cost_rows,
           0 AS incomplete_energy_buckets, 0 AS incomplete_carbon_buckets
    FROM gold.cost_monthly WHERE run_id = getvariable('gold_run_id')
    UNION ALL
    SELECT report_month, subject_id, provider, department, tool, location,
           NULL, NULL, NULL, energy_kwh, location_kg, swiss_operating_kg_co2e, reporting_kg_co2e, 0,
           CASE WHEN energy_coverage = 'complete' THEN 0 ELSE 1 END,
           CASE WHEN reporting_kg_co2e IS NOT NULL AND energy_coverage = 'complete' THEN 0 ELSE 1 END
    FROM gold.impact_monthly
    WHERE run_id = getvariable('gold_run_id') AND scenario = getvariable('gold_scenario')
), labelled AS (
    SELECT *, CASE getvariable('gold_group_by')
        WHEN 'provider' THEN provider WHEN 'department' THEN department WHEN 'tool' THEN tool
        WHEN 'location' THEN location WHEN 'subject' THEN subject_id END AS driver
    FROM metrics
), totals AS (
    SELECT report_month, driver, sum(recorded_cost_chf) AS recorded_cost_chf,
           sum(imputed_cost_chf) AS imputed_cost_chf, sum(recovered_cost_chf) AS recovered_cost_chf,
           sum(energy_kwh) AS estimated_kwh, sum(location_kg) AS estimated_location_kg,
           sum(swiss_operating_kg_co2e) AS swiss_operating_kg_co2e,
           sum(reporting_kg_co2e) AS reporting_kg_co2e,
           sum(unresolved_cost_rows) AS unresolved_cost_rows,
           sum(incomplete_energy_buckets) AS incomplete_energy_buckets,
           sum(incomplete_carbon_buckets) AS incomplete_carbon_buckets
    FROM labelled WHERE driver IS NOT NULL
    GROUP BY GROUPING SETS ((report_month, driver), (driver))
)
SELECT *,
       CASE WHEN recorded_cost_chf IS NOT NULL THEN
           dense_rank() OVER (PARTITION BY report_month ORDER BY recorded_cost_chf DESC NULLS LAST) END AS spend_rank,
       CASE WHEN reporting_kg_co2e IS NOT NULL THEN
           dense_rank() OVER (PARTITION BY report_month ORDER BY reporting_kg_co2e DESC NULLS LAST) END AS emissions_rank
FROM totals ORDER BY report_month NULLS FIRST, spend_rank NULLS LAST, driver;

-- Q03. Subtotals and missing costs by billing stream for the finance reconciliation.
SELECT cost_stream, sum(recorded_cost_chf) AS recorded_cost_chf,
       sum(included_rows) AS included_rows, sum(missing_amount_rows) AS missing_amount_rows,
       sum(missing_fx_rows) AS missing_fx_rows, sum(review_rows) AS review_rows
FROM gold.cost_monthly WHERE run_id = getvariable('gold_run_id')
GROUP BY cost_stream ORDER BY recorded_cost_chf DESC NULLS LAST;

-- Q04. August-style seat snapshot. The priced subtotal covers only known rows.
WITH seats AS (
    SELECT *, CASE WHEN active_seats BETWEEN 0 AND purchased_seats
                   THEN purchased_seats - active_seats END AS unused_seats
    FROM gold.licence_monthly
    WHERE run_id = getvariable('gold_run_id') AND report_month = getvariable('gold_seat_month')
)
SELECT licence_type, provider, product_name, sum(purchased_seats) AS known_purchased_seats,
       sum(active_seats) AS known_active_seats, sum(unused_seats) AS known_unused_seats,
       sum(unused_seats * monthly_price_per_seat_chf) AS priced_unused_chf_month,
       count(*) FILTER (WHERE unused_seats IS NULL) AS rows_with_unknown_utilisation,
       count(*) FILTER (WHERE unused_seats > 0 AND monthly_price_per_seat_chf IS NULL) AS unpriced_unused_rows
FROM seats GROUP BY licence_type, provider, product_name
ORDER BY priced_unused_chf_month DESC NULLS LAST, product_name;

-- Q05. Contract-level seat and renewal review (dates remain candidates for confirmation).
SELECT contract_key, licence_type, product_name, department, purchased_seats, active_seats,
       billing_cycle, contract_end, notice_period_days, r.decision_as_of,
       contract_end - notice_period_days AS indicative_notice_deadline,
       CASE WHEN indicative_notice_deadline IS NULL THEN 'unknown'
            WHEN indicative_notice_deadline < r.decision_as_of THEN 'past'
            ELSE 'upcoming' END AS indicative_notice_timing,
       l.evidence_set_id
FROM gold.licence_monthly AS l JOIN gold.analysis_run AS r USING (run_id)
WHERE l.run_id = getvariable('gold_run_id') AND report_month = getvariable('gold_seat_month')
  AND (purchased_seats > active_seats OR purchased_seats IS NULL OR active_seats IS NULL)
ORDER BY indicative_notice_deadline NULLS LAST, product_name, department;

-- Q06. Findings register with separately estimated measure impacts.
SELECT f.finding_id, f.subject_id, f.category, f.observed_start, f.observed_end_exclusive,
       f.observed_fact, f.waste_hypothesis, f.verification_status, f.confidence,
       m.measure_id, m.safety_status, ms.estimate_status,
       ms.gross_avoided_chf - ms.new_recurring_chf AS potential_net_chf,
       ms.before_location_kg - ms.after_location_kg AS potential_location_kg,
       f.evidence_set_id
FROM gold.finding AS f
LEFT JOIN gold.measure AS m USING (run_id, finding_id)
LEFT JOIN gold.measure_scenario AS ms
    ON ms.run_id = m.run_id AND ms.measure_id = m.measure_id
    AND ms.scenario = getvariable('gold_scenario') AND ms.horizon = getvariable('gold_horizon')
WHERE f.run_id = getvariable('gold_run_id')
ORDER BY potential_net_chf DESC NULLS LAST, f.finding_id, m.measure_id;

-- Q07. Compare hours/energy decisions such as GPU on-demand across scenarios and horizons.
SELECT m.measure_id, m.subject_id, m.proposed_change, m.earliest_effective_date,
       m.effort_person_days, m.one_time_cash_chf,
       m.effort_person_days * r.day_rate_chf + m.one_time_cash_chf AS implementation_chf,
       m.safety_status, ms.scenario, ms.horizon, ms.estimate_status,
       ms.gross_avoided_chf, ms.new_recurring_chf, ms.gross_avoided_chf - ms.new_recurring_chf AS net_chf,
       ms.before_energy_kwh - ms.after_energy_kwh AS savings_kwh,
       ms.before_location_kg - ms.after_location_kg AS savings_location_kg,
       r.emissions_basis, m.risks_and_exceptions, m.evidence_set_id AS decision_evidence,
       ms.evidence_set_id AS calculation_evidence
FROM gold.measure AS m
JOIN gold.analysis_run AS r USING (run_id)
LEFT JOIN gold.measure_scenario AS ms USING (run_id, measure_id)
WHERE m.run_id = getvariable('gold_run_id') AND m.subject_id = getvariable('gold_subject_id')
ORDER BY m.measure_id, ms.horizon, CASE ms.scenario WHEN 'low' THEN 1 WHEN 'mid' THEN 2 WHEN 'high' THEN 3 END;

-- Q08. Protection windows intersecting a proposed action and time interval.
-- A zero-row result represents no matching published window. Consult Q09 for the decision.
SELECT p.protection_id, p.rule_key, p.action_scope,
       p.starts_at AT TIME ZONE 'UTC' AS starts_at_utc, p.ends_at AT TIME ZONE 'UTC' AS ends_at_utc,
       r.schedule_timezone,
       p.decision, p.responsible_role, p.reason, p.evidence_set_id
FROM gold.protection_window AS p JOIN gold.analysis_run AS r USING (run_id)
WHERE p.run_id = getvariable('gold_run_id') AND p.subject_id = getvariable('gold_subject_id')
  AND p.action_scope IN (getvariable('gold_action'), 'all')
  AND getvariable('gold_window_start') < getvariable('gold_window_end')
  AND (p.starts_at IS NULL OR p.starts_at < getvariable('gold_window_end'))
  AND (p.ends_at IS NULL OR p.ends_at > getvariable('gold_window_start'))
ORDER BY p.starts_at NULLS FIRST, p.protection_id;

-- Q09. Blocked actions and work requiring a human decision.
SELECT m.measure_id, m.subject_id, m.description, m.safety_status,
       coalesce(m.responsible_role, s.responsible_role) AS responsible_role,
       m.risks_and_exceptions, m.earliest_effective_date, m.evidence_set_id
FROM gold.measure AS m JOIN gold.subject AS s USING (run_id, subject_id)
WHERE m.run_id = getvariable('gold_run_id') AND m.safety_status IN ('blocked', 'human_review')
ORDER BY m.safety_status, m.subject_id, m.measure_id;

-- Q10. Selected package scorecard. Percentage columns are fractional ratios.
WITH score AS (
    SELECT p.*, r.emissions_basis, r.cost_coverage, r.energy_coverage, r.carbon_coverage,
           p.baseline_cost_chf - p.net_savings_chf AS after_cost_chf,
           p.baseline_energy_kwh - p.savings_energy_kwh AS after_energy_kwh,
           p.baseline_location_kg - p.savings_location_kg AS after_location_kg,
           p.net_savings_chf / nullif(p.baseline_cost_chf, 0) AS cost_reduction,
           p.savings_location_kg / nullif(p.baseline_location_kg, 0) AS carbon_reduction,
           p.net_savings_chf - p.baseline_cost_chf * r.cost_reduction_target AS cost_margin_chf,
           p.savings_location_kg - p.baseline_location_kg * r.carbon_reduction_target AS carbon_margin_kg,
           r.implementation_cap_chf - p.implementation_chf AS budget_remaining_chf
    FROM gold.package_result AS p JOIN gold.analysis_run AS r USING (run_id)
    WHERE p.run_id = getvariable('gold_run_id') AND p.package_id = getvariable('gold_package_id')
), assessed AS (
    SELECT *, CASE
        WHEN package_kind = 'conditional' THEN 'conditional'
        WHEN evaluation_status <> 'evaluated' OR emissions_basis <> 'CO2'
          OR cost_coverage <> 'complete' OR carbon_coverage <> 'complete'
          OR cost_margin_chf IS NULL OR carbon_margin_kg IS NULL OR budget_remaining_chf IS NULL
          OR baseline_cost_chf <= 0 OR baseline_location_kg <= 0 THEN 'unassessed'
        WHEN cost_margin_chf >= 0 AND carbon_margin_kg >= 0 AND budget_remaining_chf >= 0 THEN 'meets_targets'
        ELSE 'misses_targets' END AS target_status
    FROM score
)
SELECT *, CASE WHEN count(*) OVER (PARTITION BY horizon) = 3
                  AND bool_and(target_status IN ('meets_targets', 'misses_targets')) OVER (PARTITION BY horizon) THEN
                  bool_and(target_status = 'meets_targets') OVER (PARTITION BY horizon) END AS meets_all_three_scenarios
FROM assessed
ORDER BY horizon, CASE scenario WHEN 'low' THEN 1 WHEN 'mid' THEN 2 WHEN 'high' THEN 3 END;

-- Q11. Check constraints for selected measures. Every result needs review.
WITH selected AS (
    SELECT * FROM gold.package_member
    WHERE run_id = getvariable('gold_run_id') AND package_id = getvariable('gold_package_id')
      AND scenario = getvariable('gold_scenario') AND horizon = getvariable('gold_horizon')
)
SELECT c.measure_id, c.related_measure_id, c.constraint_type, c.resolution_note, c.evidence_set_id
FROM gold.measure_constraint AS c
JOIN selected AS s USING (run_id, measure_id)
LEFT JOIN selected AS related ON related.run_id = c.run_id AND related.measure_id = c.related_measure_id
WHERE (c.constraint_type = 'requires' AND related.measure_id IS NULL)
   OR (c.constraint_type IN ('excludes', 'overlaps') AND related.measure_id IS NOT NULL)
ORDER BY c.measure_id, c.related_measure_id;

-- Q12. Follow a dashboard row back to source records, assumptions and formulas.
SELECT e.evidence_type, e.source_file, e.source_row, e.source_record_id, e.detail,
       e.factor_id, f.factor_name, f.value_low, f.value_mid, f.value_high, f.value_text,
       f.unit, f.source_reference, f.source_date, f.definition_and_rationale
FROM gold.evidence AS e LEFT JOIN gold.factor AS f USING (run_id, factor_id)
WHERE e.run_id = getvariable('gold_run_id') AND e.evidence_set_id = getvariable('gold_evidence_set_id')
ORDER BY e.evidence_no;

-- Q13. Compare persisted package results with the credited contribution ledger.
-- Review missing member amounts separately because SUM skips NULLs.
WITH credit AS (
    SELECT pm.run_id, pm.package_id, pm.scenario, pm.horizon, count(*) AS members,
           count(*) FILTER (WHERE m.safety_status <> 'eligible') AS noneligible_members,
           count(*) FILTER (WHERE pm.credited_cost_chf IS NULL OR pm.credited_energy_kwh IS NULL
                              OR pm.credited_location_kg IS NULL OR pm.credited_implementation_chf IS NULL) AS partial_members,
           sum(pm.credited_cost_chf) AS member_cost, sum(pm.credited_energy_kwh) AS member_energy,
           sum(pm.credited_location_kg) AS member_carbon, sum(pm.credited_implementation_chf) AS member_implementation
    FROM gold.package_member AS pm JOIN gold.measure AS m USING (run_id, measure_id)
    WHERE pm.run_id = getvariable('gold_run_id') AND pm.package_id = getvariable('gold_package_id')
    GROUP BY pm.run_id, pm.package_id, pm.scenario, pm.horizon
)
SELECT p.scenario, p.horizon, p.package_kind, p.evaluation_status,
       coalesce(c.members, 0) AS members, coalesce(c.partial_members, 0) AS partial_members,
       p.package_kind = 'automatic' AND coalesce(c.noneligible_members, 0) > 0 AS automatic_safety_violation,
       p.net_savings_chf IS DISTINCT FROM CASE WHEN c.members IS NULL THEN 0 ELSE c.member_cost END AS cost_differs,
       p.savings_energy_kwh IS DISTINCT FROM CASE WHEN c.members IS NULL THEN 0 ELSE c.member_energy END AS energy_differs,
       p.savings_location_kg IS DISTINCT FROM CASE WHEN c.members IS NULL THEN 0 ELSE c.member_carbon END AS carbon_differs,
       p.implementation_chf IS DISTINCT FROM CASE WHEN c.members IS NULL THEN 0 ELSE c.member_implementation END AS budget_differs
FROM gold.package_result AS p LEFT JOIN credit AS c USING (run_id, package_id, scenario, horizon)
WHERE p.run_id = getvariable('gold_run_id') AND p.package_id = getvariable('gold_package_id')
ORDER BY p.horizon, p.scenario;

-- Q14. Prepare rows for the official baseline and assumptions CSV.
WITH template(seq, parameter, must_or_bonus, unit) AS (VALUES
    (1, 'total_cost_baseline_year_chf', 'Must', 'CHF per year'),
    (2, 'total_energy_baseline_year_kwh', 'Must', 'kWh per year'),
    (3, 'total_co2_location_based_baseline_year_kg', 'Must', 'kg CO2 per year'),
    (4, 'total_co2_market_based_baseline_year_kg', 'Bonus', 'kg CO2 per year'),
    (5, 'grid_mix_location_based_switzerland', 'Must', 'kg CO2 per kWh'),
    (6, 'grid_mix_location_based_germany', 'Must', 'kg CO2 per kWh'),
    (7, 'grid_mix_location_based_ireland', 'Must', 'kg CO2 per kWh'),
    (8, 'grid_mix_market_based', 'Bonus', 'kg CO2 per kWh'),
    (9, 'energy_per_vcpu_hour', 'Must', 'kWh'),
    (10, 'energy_per_node_hour', 'Must', 'kWh'),
    (11, 'energy_per_gpu_hour', 'Must', 'kWh'),
    (12, 'energy_per_gb_storage_day', 'Must', 'kWh'),
    (13, 'energy_per_1000_tokens', 'Must', 'kWh'),
    (14, 'energy_per_subscription_message', 'Must', 'kWh'),
    (15, 'pue', 'Must', 'ratio'),
    (16, 'growth_per_year', 'Bonus', 'percent'),
    (17, 'allocation_rule_shared_costs', 'Must', 'text')
), costs AS (
    SELECT sum(recorded_cost_chf) AS recorded_chf, sum(imputed_cost_chf) AS imputed_chf FROM gold.cost_monthly WHERE run_id = getvariable('gold_run_id')
), impacts AS (
    SELECT scenario, sum(energy_kwh) AS estimated_kwh, sum(location_kg) AS estimated_location_kg
    FROM gold.impact_monthly WHERE run_id = getvariable('gold_run_id') GROUP BY scenario
), totals AS (
    SELECT 'total_cost_baseline_year_chf' AS parameter, NULL AS value_low, coalesce(c.recorded_chf + coalesce(c.imputed_chf, 0), c.imputed_chf) AS value_mid, NULL AS value_high,
           'Silver cost_facts.csv; run ' || r.run_id AS source,
           concat('September 2025 through August 2026. Recorded CHF ', c.recorded_chf, '; comparable-price imputation CHF ', coalesce(c.imputed_chf, 0), '; coverage ', r.cost_coverage, '. Unresolved charges remain outside the modeled subtotal.') AS explanation
    FROM costs AS c CROSS JOIN gold.analysis_run AS r WHERE r.run_id = getvariable('gold_run_id')
    UNION ALL
    SELECT 'total_energy_baseline_year_kwh', max(estimated_kwh) FILTER (WHERE scenario = 'low'),
           max(estimated_kwh) FILTER (WHERE scenario = 'mid'), max(estimated_kwh) FILTER (WHERE scenario = 'high'),
           'Gold activity and factor evidence; run ' || r.run_id, 'Estimated facility energy; coverage ' || r.energy_coverage
    FROM impacts CROSS JOIN gold.analysis_run AS r WHERE r.run_id = getvariable('gold_run_id')
    GROUP BY r.run_id, r.energy_coverage
    UNION ALL
    SELECT 'total_co2_location_based_baseline_year_kg', max(estimated_location_kg) FILTER (WHERE scenario = 'low'),
           max(estimated_location_kg) FILTER (WHERE scenario = 'mid'), max(estimated_location_kg) FILTER (WHERE scenario = 'high'),
           'Gold activity and grid-factor evidence; run ' || r.run_id,
           'Location-based estimate in kg ' || r.emissions_basis || '. Includes Swiss operating emissions and mixed-EU AI generation proxies. Coverage ' || r.carbon_coverage
    FROM impacts CROSS JOIN gold.analysis_run AS r
    WHERE r.run_id = getvariable('gold_run_id') GROUP BY r.run_id, r.carbon_coverage, r.emissions_basis
)
SELECT t.parameter, t.must_or_bonus, cast(coalesce(b.value_low, f.value_low) AS VARCHAR) AS value_low,
       coalesce(cast(b.value_mid AS VARCHAR), cast(f.value_mid AS VARCHAR), f.value_text) AS value_mid,
       cast(coalesce(b.value_high, f.value_high) AS VARCHAR) AS value_high,
       t.unit, coalesce(b.source, f.source_reference) AS source,
       coalesce(b.explanation, CASE WHEN f.factor_id IS NOT NULL THEN
           concat_ws(' | ', f.definition_and_rationale, 'Source date ' || f.source_date) END) AS calculation_or_assumption
FROM template AS t JOIN gold.analysis_run AS r ON r.run_id = getvariable('gold_run_id')
LEFT JOIN totals AS b USING (parameter)
LEFT JOIN gold.factor AS f ON f.submission_parameter = t.parameter AND f.run_id = r.run_id
    AND t.must_or_bonus = 'Must' AND t.seq > 4
ORDER BY t.seq;

-- Q15. Prepare one official measures CSV row per selected package member.
WITH evidence_summary AS (
    SELECT run_id, evidence_set_id,
           string_agg(concat_ws(' ', detail, source_file,
               CASE WHEN source_row IS NOT NULL THEN 'row ' || source_row END,
               f.source_reference), ' | ' ORDER BY evidence_no) AS calculation_sources
    FROM gold.evidence LEFT JOIN gold.factor AS f USING (run_id, factor_id)
    WHERE run_id = getvariable('gold_run_id') AND evidence_type IN ('calculation', 'assumption', 'ticket')
    GROUP BY run_id, evidence_set_id
)
SELECT m.measure_id, m.description, s.subject_name AS resource_or_source, m.proposed_change AS change,
       m.effort_person_days, pm.credited_cost_chf AS savings_cost_chf_per_year,
       pm.credited_energy_kwh AS savings_energy_kwh_per_year,
       pm.credited_location_kg AS savings_co2_kg_location_based,
       NULL::DECIMAL(28, 12) AS savings_co2_kg_market_based,
       concat_ws(' | ', m.risks_and_exceptions, 'Responsible owner: ' || m.responsible_role) AS risks_and_exceptions,
       concat_ws(' | ', 'Run ' || pm.run_id, 'Package ' || pm.package_id, pm.horizon, pm.scenario,
                 p.evaluation_status, 'Location savings in kg ' || r.emissions_basis, 'Effective from ' || m.earliest_effective_date,
                 'Contribution evidence ' || pm.evidence_set_id, 'Decision evidence ' || m.evidence_set_id,
                 'One-time cash CHF ' || m.one_time_cash_chf, pm.allocation_note,
                 ce.calculation_sources, de.calculation_sources) AS assumptions_and_sources
FROM gold.package_member AS pm JOIN gold.measure AS m USING (run_id, measure_id)
JOIN gold.subject AS s ON s.run_id = m.run_id AND s.subject_id = m.subject_id
JOIN gold.package_result AS p USING (run_id, package_id, scenario, horizon)
JOIN gold.analysis_run AS r USING (run_id)
LEFT JOIN evidence_summary AS ce ON ce.run_id = pm.run_id AND ce.evidence_set_id = pm.evidence_set_id
LEFT JOIN evidence_summary AS de ON de.run_id = m.run_id AND de.evidence_set_id = m.evidence_set_id
WHERE pm.run_id = getvariable('gold_run_id') AND pm.package_id = getvariable('gold_package_id')
  AND pm.scenario = getvariable('gold_scenario') AND pm.horizon = getvariable('gold_horizon')
  AND (m.safety_status = 'eligible' OR (p.package_kind = 'conditional' AND m.safety_status = 'human_review'))
ORDER BY m.measure_id;
