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

CANONICAL_FIELDS = 'source_file source_row event_date resource_id provider cost_center department tool region quantity unit amount_original currency fx_rate cost_chf quality_flags'.split()


def canonical_mapping(name):
    """Planning mappings only; these expressions are never evaluated as ETL."""
    spec = SPECS[name]
    mapping = {f: {'source': 'unknown', 'rule': 'Not recorded or not applicable in this source; preserve null.'} for f in CANONICAL_FIELDS}
    def put(field, source, rule='Direct source value; no transformation in Phase 2.'):
        mapping[field] = {'source': source, 'rule': rule}
    put('source_file', 'provenance', name)
    put('source_row', 'provenance', '1-based logical CSV record, header is record 1; not physical line number.')
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
