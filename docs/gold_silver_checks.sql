-- Run in local DuckDB. Set silver_dir to the folder selected by outputs/current_silver.csv.
-- The views read the published Silver CSVs. Source data stays unchanged.
CREATE TEMP VIEW silver_costs AS
SELECT *, cast(cost_chf AS DECIMAL(28, 12)) AS amount_chf
FROM read_csv(getvariable('silver_dir') || '/cost_facts.csv', all_varchar = true);

CREATE TEMP VIEW silver_baseline AS
SELECT * FROM read_csv(getvariable('silver_dir') || '/cost_baseline.csv', all_varchar = true);

-- S01. Reconcile the current Silver financial baseline and quantify coverage.
WITH actual AS (
    SELECT sum(amount_chf) FILTER (WHERE financial_status = 'included') AS recorded_cost_chf,
           count(*) FILTER (WHERE financial_status = 'included') AS included_rows,
           count(*) FILTER (WHERE financial_status = 'missing_amount') AS missing_amount_rows,
           count(*) FILTER (WHERE financial_status = 'missing_fx') AS missing_fx_rows,
           count(*) FILTER (WHERE financial_status = 'review') AS review_rows_full_export
    FROM silver_costs
)
SELECT b.silver_version, b.start, b."end", a.*, b.coverage_status,
       a.recorded_cost_chf = b.recorded_cost_chf::DECIMAL(28, 12)
         AND a.included_rows = b.included::BIGINT AND a.missing_amount_rows = b.missing_amount::BIGINT
         AND a.missing_fx_rows = b.missing_fx::BIGINT AS reconciles,
       round(a.recorded_cost_chf * 0.25, 2) AS quarter_of_recorded_subtotal_chf
FROM silver_baseline AS b CROSS JOIN actual AS a;

-- S02. August 2026 purchased and active AI seats and priced monthly unused seats.
WITH contracts AS (
    SELECT product, provider, contract_end::DATE AS end_date, notice_period_days::INTEGER AS notice_days,
           licences_purchased::INTEGER AS purchased, licences_active_30d::INTEGER AS active,
           price_per_seat::DECIMAL(12, 4) * fx_rate::DECIMAL(12, 8) AS price_per_seat_chf
    FROM read_csv(getvariable('silver_dir') || '/ai_subscriptions.csv', all_varchar = true)
    WHERE record_status = 'accepted' AND contract_status = 'Final' AND reporting_month = '2026-08'
), seats AS (
    SELECT *, CASE WHEN active BETWEEN 0 AND purchased THEN purchased - active END AS unused FROM contracts
)
SELECT product, provider, sum(purchased) AS known_purchased, sum(active) AS known_active,
       sum(unused) AS known_unused, round(sum(unused * price_per_seat_chf), 2) AS priced_unused_chf_month,
       count(*) FILTER (WHERE unused IS NULL) AS unknown_utilisation_rows,
       count(*) FILTER (WHERE unused > 0 AND price_per_seat_chf IS NULL) AS unpriced_unused_rows,
       min(end_date) AS earliest_contract_end, min(end_date - notice_days) AS earliest_indicative_notice_deadline
FROM seats GROUP BY product, provider ORDER BY known_unused DESC NULLS LAST;

-- S03. dp-dev usage and observation coverage in the official baseline.
WITH observations AS (
    SELECT * FROM read_csv(getvariable('silver_dir') || '/data_platform_usage.csv', all_varchar = true)
    WHERE resource_id = 'dp-dev' AND record_status = 'accepted'
      AND event_date::DATE >= DATE '2025-09-01' AND event_date::DATE < DATE '2026-09-01'
)
SELECT date_diff('day', DATE '2025-09-01', DATE '2026-09-01') AS expected_days,
       count(DISTINCT event_date) AS observed_days,
       expected_days - observed_days AS days_without_accepted_records,
       count(runtime_h) AS runtime_observations, count(active_use_h) AS activity_observations,
       sum(runtime_h::DECIMAL(16, 4)) AS recorded_cluster_runtime_h,
       sum(active_use_h::DECIMAL(16, 4)) AS recorded_active_cluster_h,
       sum(node_hours::DECIMAL(16, 4)) AS recorded_node_hours
FROM observations;

-- S04. GPU invoice and observed instance activity, shown with attribution status.
WITH billing AS (
    SELECT sum(amount_chf) FILTER (WHERE financial_status = 'included') AS recorded_gpu_resource_cost_chf,
           count(*) FILTER (WHERE financial_status IN ('missing_amount', 'missing_fx')) AS missing_cost_rows
    FROM silver_costs WHERE source_file = 'azure_costs.csv' AND resource_id = 'gpu-ml'
), monitoring AS (
    SELECT count(*) AS complete_baseline_week_records, count(gpu_avg_pct) AS gpu_observations,
           avg(gpu_avg_pct::DECIMAL(12, 4)) AS mean_of_weekly_gpu_pct, sum(uptime_h::DECIMAL(14, 4)) AS observed_uptime_h
    FROM read_csv(getvariable('silver_dir') || '/server_metrics_weekly.csv', all_varchar = true)
    WHERE record_status = 'accepted' AND server_id = 'gpu-ml-01'
      AND event_date::DATE >= DATE '2025-09-01' AND week_end::DATE < DATE '2026-09-01'
)
SELECT 'gpu-ml' AS billed_resource, 'gpu-ml-01' AS observed_server, rel.confidence AS attribution_status,
       billing.*, monitoring.*, rel.evidence
FROM billing CROSS JOIN monitoring
LEFT JOIN read_csv(getvariable('silver_dir') || '/resource_relationships.csv', all_varchar = true) AS rel
    ON rel.resource_id = 'gpu-ml' AND rel.server_id = 'gpu-ml-01';

-- S05. Observed dp-prod activity on Basel workdays, weekends and other non-workdays.
-- Daily observations provide evidence about dates. Ticket evidence supplies time-of-day context.
WITH observations AS (
    SELECT event_date::DATE AS day, active_use_h::DECIMAL(16, 4) AS active_h, query_count::BIGINT AS queries
    FROM read_csv(getvariable('silver_dir') || '/data_platform_usage.csv', all_varchar = true)
    WHERE resource_id = 'dp-prod' AND record_status = 'accepted'
), calendar AS (
    SELECT event_date::DATE AS day, CASE
        WHEN weekday_iso::INTEGER IN (6, 7) THEN 'weekend'
        WHEN workday::BOOLEAN THEN 'workday' ELSE 'other_non_workday' END AS day_type
    FROM read_csv(getvariable('silver_dir') || '/business_calendar.csv', all_varchar = true)
    WHERE record_status = 'accepted' AND event_date::DATE >= DATE '2025-09-01' AND event_date::DATE < DATE '2026-09-01'
), daily AS (
    SELECT day, sum(active_h) AS active_h, sum(queries) AS queries FROM observations GROUP BY day
)
SELECT day_type, count(*) AS calendar_days, count(d.day) AS days_with_observations,
       count(*) FILTER (WHERE d.active_h > 0 OR d.queries > 0) AS known_days_with_activity,
       sum(d.active_h) AS recorded_active_cluster_h, sum(d.queries) AS recorded_queries
FROM calendar AS c LEFT JOIN daily AS d USING (day)
GROUP BY day_type ORDER BY day_type;

-- S06. Ticket evidence for safety review. Interpret against asset scope and validity.
SELECT ticket_id, event_date, resource_id AS structured_resource_id, resource_mentions, status,
       title, description, source_file, source_row::BIGINT AS source_row, record_id
FROM read_csv(getvariable('silver_dir') || '/it_tickets.csv', all_varchar = true)
WHERE record_status = 'accepted'
  AND ticket_id IN ('T-1029', 'T-1039', 'T-1053', 'T-1094', 'T-1101', 'T-1167', 'T-1195', 'T-1204')
ORDER BY ticket_id;

-- S07. Expensive AI gateway workloads by task, department and model.
-- Stable record_id connects each accepted activity row to at most one financial record.
WITH usage AS (
    SELECT record_id, task_type, model, provider, consumer_department, requests::BIGINT AS requests,
           uncached_input_tokens::BIGINT AS uncached, tokens_in_cache::BIGINT AS cached, tokens_out::BIGINT AS output_tokens
    FROM read_csv(getvariable('silver_dir') || '/ai_usage.csv', all_varchar = true)
    WHERE record_status = 'accepted' AND event_date::DATE >= DATE '2025-09-01' AND event_date::DATE < DATE '2026-09-01'
)
SELECT u.task_type, u.model, u.provider, u.consumer_department,
       sum(u.requests) AS recorded_requests, sum(u.uncached) AS uncached_input_tokens,
       sum(u.cached) AS cached_input_tokens, sum(u.output_tokens) AS recorded_output_tokens,
       count(*) FILTER (WHERE u.output_tokens IS NULL) AS missing_output_rows,
       sum(c.amount_chf) FILTER (WHERE c.financial_status = 'included') AS recorded_cost_chf
FROM usage AS u LEFT JOIN silver_costs AS c ON u.record_id = c.record_id AND c.source_file = 'ai_usage.csv'
GROUP BY u.task_type, u.model, u.provider, u.consumer_department
ORDER BY recorded_cost_chf DESC NULLS LAST, u.task_type, u.model, u.provider, u.consumer_department;
