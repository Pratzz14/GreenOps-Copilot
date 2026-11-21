"""Versioned dictionary contracts, independent of observed CSV contents."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    role: str
    fields: str
    key: str
    date: str = ""
    entity: str = ""
    cadence: str = "daily"
    amount: str = ""
    currency: str = ""
    resource: str = ""
    center: str = ""

    @property
    def types(self):
        return dict(token.split(":") if ":" in token else (token, "text") for token in self.fields.split())


SPECS = {
    'azure_costs.csv': Spec('Provider charges', 'Date:date ResourceId ServiceName ResourceLocation Quantity:number UnitOfMeasure CostInBillingCurrency:number BillingCurrency ChargeType Tags:json AvgCpuPercent:number Notes', 'Date ResourceId ChargeType UnitOfMeasure BillingCurrency', 'Date', 'ResourceId', amount='CostInBillingCurrency', currency='BillingCurrency', resource='ResourceId'),
    'aws_costs.csv': Spec('Provider charges', 'line_item_usage_start_date:timestamp line_item_resource_id product_servicecode product_region line_item_usage_amount:number pricing_unit line_item_unblended_cost:number line_item_currency_code line_item_line_item_type resource_tags_user_department resource_tags_user_tool resource_tags_user_project resource_tags_user_environment avg_cpu_utilization:number object_requests:number line_item_description', 'line_item_usage_start_date line_item_resource_id line_item_line_item_type pricing_unit line_item_currency_code', 'line_item_usage_start_date', 'line_item_resource_id', amount='line_item_unblended_cost', currency='line_item_currency_code', resource='line_item_resource_id'),
    'hoster_invoice.csv': Spec('Provider charges', 'Date:swiss_date Item Service Quantity:number Unit Amount_CHF:number CostCenter ProjectNumber Accesses:number Remark', 'Date Item Service Unit CostCenter', 'Date', 'Item', amount='Amount_CHF', currency='CHF', center='CostCenter'),
    'data_platform_usage.csv': Spec('Monitoring and utilization', 'date:date resource_id cluster region node_count:number runtime_h:number active_use_h:number query_count:number', 'date resource_id cluster', 'date', 'resource_id', resource='resource_id'),
    'server_inventory.csv': Spec('Asset inventory', 'server_id provider region vcpu:number ram_gb:number type owner_cost_center created:date last_login:date cpu_utilisation_30d_pct:number ram_utilisation_30d_pct:number runtime_h_30d:number tags operating_system patch_level project_id environment criticality', 'server_id', cadence='snapshot', resource='server_id', center='owner_cost_center'),
    'server_metrics_weekly.csv': Spec('Monitoring and utilization', 'week_start:date server_id cpu_avg_pct:number cpu_max_pct:number ram_avg_pct:number network_gb:number uptime_h:number gpu_avg_pct:number', 'week_start server_id', 'week_start', 'server_id', 'weekly', resource='server_id'),
    'ai_usage.csv': Spec('Gateway usage with reported costs', 'date:date resource_id tool department task_type model_class provider model requests:number tokens_in:number tokens_in_cache:number tokens_out:number cost_chf:number project_id', 'date resource_id tool department task_type provider model_class model project_id', 'date', 'resource_id', amount='cost_chf', currency='CHF', resource='resource_id'),
    'ai_subscriptions.csv': Spec('Contracts with activity observations', 'month:date product provider cost_center licences_purchased:number licences_active_30d:number messages_30d:number price_per_seat:number currency amount:number contract_status contract_end:date notice_period_days:number billing', 'month product provider cost_center contract_status', 'month', 'product cost_center', 'monthly', 'amount', 'currency', center='cost_center'),
    'saas_contracts.csv': Spec('Contracts with activity observations', 'month:date contract provider cost_center licences_purchased:number licences_active_30d:number price_per_licence:number currency amount:number contract_status contract_end:date notice_period_days:number billing', 'month contract provider cost_center contract_status', 'month', 'contract cost_center', 'monthly', 'amount', 'currency', center='cost_center'),
    'mapping_departments_tools.csv': Spec('Master data', 'resource_id tool department cost_center responsible_role environment criticality default_project rechargeable', 'resource_id', cadence='master', resource='resource_id', center='cost_center'),
    'exchange_rates.csv': Spec('Master data', 'month:date eur_chf:number usd_chf:number', 'month', 'month', cadence='monthly'),
    'it_tickets.csv': Spec('Operational evidence', 'ticket_id date:date type resource_id title description status', 'ticket_id', 'date', cadence='events', resource='resource_id'),
    'business_calendar.csv': Spec('Operational evidence', 'date:date weekday workday:binary public_holiday company_holidays', 'date', 'date'),
}

EXTRA_SPECS = {
    'ai_agent_runs': Spec('AI agent execution evidence', 'run_id agent start:timestamp trigger steps:number tool_calls:number retries:number provider model tokens_in:number tokens_out:number cache_read_tokens:number duration_seconds:number outcome department project_id report_opened:binary', 'run_id', 'start', 'agent', 'events'),
    'ai_invoice_monthly': Spec('AI provider invoice comparison', 'month:date provider model_class tokens_in:number tokens_out:number currency amount:number', 'month provider model_class', 'month', 'provider model_class', 'monthly', 'amount', 'currency'),
    'backup_chains': Spec('Backup inventory and protection', 'source category backup_tool size_gb:number frequency retention_days:number last_restore_test:date second_site criticality data_class cost_center', 'source backup_tool', cadence='snapshot'),
    'ci_pipeline_runs': Spec('CI job runs and resource usage', 'pipeline repo trigger started_at:timestamp status team project_id runner duration_seconds:number cpu_h:number commits_since_last_nightly:number', 'repo pipeline started_at trigger', 'started_at', 'repo', 'events'),
    'data_catalog_tables': Spec('Table inventory and retention requirements', 'table schema size_gb:number rows:number last_read:date last_written:date owner_cost_center project_id data_class retention_required', 'schema table', cadence='snapshot'),
    'data_center_locations': Spec('Provider location catalogue', 'provider region location used_by_sme', 'provider region', cadence='master'),
    'data_platform_jobs': Spec('Job schedules and protection windows', 'date:date job_name resource_id start_time duration_h:number status triggered_by time_window', 'date resource_id job_name start_time', 'date', 'resource_id', 'events', resource='resource_id'),
    'headcount': Spec('Department allocation context', 'month:date department fte:number', 'month department', 'month', 'department', 'monthly'),
    'log_volume': Spec('Daily log ingestion and retention', 'date:date service log_gb:number unit retention_days:number project_id owner_cost_center', 'date service', 'date', 'service'),
    'm365_usage': Spec('Weekly Microsoft 365 service activity', 'week_start:date department cost_center active_users:number storage:number teams_video_minutes:number mails_sent:number storage_unit', 'week_start department', 'week_start', 'department', 'weekly'),
    'powerbi_usage': Spec('Report refresh and view activity', 'date:date resource_id report department refresh_count:number refresh_duration_min:number view_count:number active_user_count:number report_type', 'date resource_id', 'date', 'resource_id', resource='resource_id'),
    'project_hours_monthly': Spec('Project and department allocation context', 'month:date project_id department hours:number', 'month project_id department', 'month', 'project_id department', 'monthly'),
    'projects': Spec('Project master', 'project_id project_name type customer cost_center start:date end:date rechargeable status', 'project_id', cadence='master'),
    'provider_monthly_report': Spec('Provider spend comparison', 'month:date total_cost_chf:number label', 'month label', 'month', 'label', 'monthly'),
    'web_traffic': Spec('Hourly sampled CDN traffic', 'time_utc:timestamp requests:number gb_out:number bot_share_pct:number sample_rate:number status_5xx:number', 'time_utc', 'time_utc', cadence='hourly'),
}
EXTRA_FILES = {table: f"{table}.{'jsonl' if table in {'ai_agent_runs', 'ci_pipeline_runs'} else 'csv'}"
               for table in EXTRA_SPECS}
SPECS.update({EXTRA_FILES[table]: spec for table, spec in EXTRA_SPECS.items()})

# How one row should be read, and whether its quantities may be added over time.
# additivity: additive_total, mixed, period_level, point_in_time or reference.
GRAINS = {
    'azure_costs.csv': ('One billing line per resource, meter and day', 'additive_total', 'Quantities add within one unit and charges within one currency.'),
    'aws_costs.csv': ('One billing line per resource and day, with monthly support fees', 'additive_total', 'Quantities add within one pricing unit. Monthly fees are month totals.'),
    'hoster_invoice.csv': ('One invoice line per item and day', 'additive_total', 'GB and GB-days are different units and never add to each other.'),
    'data_platform_usage.csv': ('One observation per cluster and day', 'mixed', 'Runtime, active hours and queries add over days. Node count is a daily level.'),
    'server_inventory.csv': ('One server in the 2026-09-06 inventory', 'point_in_time', 'A single inventory date. Utilisation is a 30-day average and never adds.'),
    'server_metrics_weekly.csv': ('One server per week', 'mixed', 'Uptime hours and network GB are weekly totals. Percentages are weekly averages and do not add.'),
    'ai_usage.csv': ('One day per tool, department, task and model', 'additive_total', 'Requests and tokens add. Cached input is part of input.'),
    'ai_subscriptions.csv': ('One contract version per product, cost centre and month', 'mixed', 'Monthly amounts add across months. Seats and 30-day activity are month levels.'),
    'saas_contracts.csv': ('One contract version per contract, cost centre and month', 'mixed', 'Monthly amounts add across months. Seats and 30-day activity are month levels.'),
    'mapping_departments_tools.csv': ('One resource', 'reference', 'Ownership reference without a time series.'),
    'exchange_rates.csv': ('One month', 'reference', 'Monthly average rates. Rates never add.'),
    'it_tickets.csv': ('One ticket', 'reference', 'Operational evidence. Tickets can be counted but carry no quantity.'),
    'business_calendar.csv': ('One calendar day', 'reference', 'Calendar reference. Workdays can be counted.'),
    'ai_agent_runs.jsonl': ('One agent run', 'additive_total', 'Steps, retries, tokens and seconds add over runs. Cached tokens are part of input.'),
    'ai_invoice_monthly.csv': ('One invoice line per provider, model class and month', 'additive_total', 'Monthly totals. Comparison only, never added to gateway usage.'),
    'backup_chains.csv': ('One backup source and tool', 'point_in_time', 'Current backup size and settings. Sizes never add over time.'),
    'ci_pipeline_runs.jsonl': ('One pipeline run', 'additive_total', 'Seconds and CPU-hours add over runs. Reruns are separate runs.'),
    'data_catalog_tables.csv': ('One table in the 2026-09-06 catalogue', 'point_in_time', 'A single catalogue date. Sizes add across tables, never over time.'),
    'data_center_locations.csv': ('One provider region', 'reference', 'Location reference without a time series.'),
    'data_platform_jobs.csv': ('One job run', 'additive_total', 'Run hours add. The time window is a schedule rule.'),
    'headcount.csv': ('One department per month', 'period_level', 'FTE is a month level. Average it across months instead of adding.'),
    'log_volume.csv': ('One service per day', 'mixed', 'Ingested GB adds over days. Retention days is a setting.'),
    'm365_usage.csv': ('One department per week', 'mixed', 'Video minutes and mails are weekly totals. Storage and active users are weekly levels, so storage adds only as GB-days.'),
    'powerbi_usage.csv': ('One report per day', 'mixed', 'Refreshes, refresh minutes and views add. Distinct active users do not.'),
    'project_hours_monthly.csv': ('One project and department per month', 'additive_total', 'Booked hours are monthly totals.'),
    'projects.csv': ('One project', 'reference', 'Project reference without a time series.'),
    'provider_monthly_report.csv': ('One month', 'additive_total', 'Monthly totals. Comparison only, never added to the ledger.'),
    'web_traffic.csv': ('One hour in UTC', 'mixed', 'Requests and GB add after applying the sampling rate. Bot share is a ratio.'),
}


def grain(name):
    label, additivity, note = GRAINS.get(name, (None, None, None))
    return {'grain': label, 'additivity': additivity, 'additivity_note': note}


CANONICAL_FIELDS = 'source_file source_row event_date resource_id provider cost_center department tool region quantity unit amount_original currency fx_rate cost_chf quality_flags'.split()


def canonical_mapping(name):
    """Planning mappings only; these expressions are never evaluated as ETL."""
    spec = SPECS[name]
    mapping = {f: {'source': 'unknown', 'rule': 'Not recorded or not applicable in this source; preserve null.'} for f in CANONICAL_FIELDS}
    def put(field, source, rule='Direct source value; no transformation in Phase 2.'):
        mapping[field] = {'source': source, 'rule': rule}
    put('source_file', 'provenance', name)
    put('source_row', 'provenance', '1-based physical JSONL line.' if name.endswith('.jsonl')
        else '1-based logical CSV record, header is record 1; not physical line number.')
    if spec.date: put('event_date', spec.date, f'Parse documented {spec.types[spec.date]} format; retain raw value.')
    if spec.resource: put('resource_id', spec.resource, 'Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs.')
    if spec.center: put('cost_center', spec.center)
    for field in ('provider', 'department', 'tool', 'region'):
        if field in spec.types: put(field, field)
    if name == 'azure_costs.csv':
        for f, col in [('provider','constant Azure'),('department','Tags.department'),('tool','Tags.tool'),('region','ResourceLocation'),('quantity','Quantity'),('unit','UnitOfMeasure')]: put(f,col)
    if name == 'aws_costs.csv':
        for f, col in [('provider','constant AWS'),('department','resource_tags_user_department'),('tool','resource_tags_user_tool'),('region','product_region'),('quantity','line_item_usage_amount'),('unit','pricing_unit')]: put(f,col)
    if name == 'hoster_invoice.csv':
        for f,col in [('provider','constant Swiss hoster'),('tool','Item'),('quantity','Quantity'),('unit','Unit')]: put(f,col)
        put('resource_id','Item → mapping.tool','Proposed label lookup only if unique; otherwise unknown.')
    if spec.resource or spec.center:
        for f in ('department','tool','cost_center'):
            if mapping[f]['source']=='unknown': put(f,'mapping_departments_tools.csv', 'Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated).')
    if spec.amount:
        put('amount_original',spec.amount)
        put('currency',spec.currency)
        put('fx_rate','exchange_rates.csv', 'Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null.')
        put('cost_chf',spec.amount if spec.currency=='CHF' else 'derived in Phase 3','Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2.')
    put('quality_flags','profiling issues','Attach source-row issues without deleting records.')
    return mapping
