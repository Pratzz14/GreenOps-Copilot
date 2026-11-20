"""Source-specific Silver validation and enrichment rules."""
import calendar
import json
import re
from datetime import date, timedelta
from decimal import Decimal

from src.profile import END, START

FREE_TEXT = {'notes', 'remark', 'line_item_description', 'title', 'description'}
OPTIONAL = FREE_TEXT | {'public_holiday', 'company_holidays', 'tags', 'resource_mentions'}
UNITS = {name.casefold(): name for name in (
    'GB', 'GB-day', 'GB-month', 'vCore-hour', 'vCPU-hour', 'GPU-hour', 'node-hour',
    'month', 'hour', 'runner-minute', 'TB', 'CU-hour', 'request', 'million requests',
    'TB-day', 'capacity-day', 'instance-hour', 'VM-hour', 'capacity-hour',
)}
REGIONS = {
    'switzerland (zurich)': 'Switzerland (Zurich)',
    'germany (frankfurt)': 'Germany (Frankfurt)',
    'ireland (dublin)': 'Ireland (Dublin)',
    'switzerland (basel)': 'Switzerland (Basel)',
}
PROVIDERS = {value.casefold(): value for value in (
    'Azure', 'AWS', 'Swiss Hoster', 'Azure OpenAI', 'OpenAI', 'Anthropic', 'Microsoft',
)}
MODELS = {value.casefold(): value for value in (
    'GPT-5.4', 'GPT-5.4 mini', 'Azure OpenAI GPT-5.4', 'Azure OpenAI GPT-5.4 mini',
    'Claude Sonnet 4.6', 'Claude Haiku 4.5', 'GPT-5', 'GPT-5-mini', 'GPT-4.1-mini',
    'GPT-4o', 'GPT-4o-mini', 'o3', 'o4-mini',
)}
AGGREGATES = {'azure_costs', 'aws_costs', 'data_platform_usage', 'server_metrics_weekly',
              'business_calendar', 'exchange_rates'}
CONTRACTS = {'ai_subscriptions', 'saas_contracts'}
USAGE = {'data_platform_usage', 'server_metrics_weekly', 'ai_usage'}
GPU_TYPES = {'ml', 'gpu'}
NON_GPU_TYPES = {'prod', 'test', 'poc', 'dev', 'dr', 'backup', 'storage', 'archive', 'db', 'batch', 'other'}


def slug(value):
    value = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', value)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value).lower()


def project(value):
    match = re.fullmatch(r'p-?(\d{3})', value, re.IGNORECASE)
    return f'P-{match[1]}' if match else None


def classify(field, value):
    folded = value.casefold()
    if field in {'region', 'product_region', 'resource_location'}:
        return REGIONS.get(' '.join(folded.split()), value), 'region_alias'
    if field in {'unit', 'unit_of_measure', 'pricing_unit'}:
        return UNITS.get(folded, value), 'unit_alias'
    if field == 'provider':
        return PROVIDERS.get(folded, value), 'provider_alias'
    if field == 'model':
        return MODELS.get(folded, value), 'model_alias'
    if field in {'environment', 'criticality', 'model_class', 'type', 'status', 'billing',
                 'resource_tags_user_environment', 'patch_level'}:
        return folded, 'classification'
    if field in {'contract_status', 'charge_type', 'line_item_line_item_type'}:
        return value.capitalize(), 'classification'
    if field in {'currency', 'billing_currency', 'line_item_currency_code', 'ticket_id'}:
        return value.upper(), 'classification'
    if field in {'resource_id', 'server_id'}:
        return folded, 'resource_identifier'
    return value, 'trim'


def metrics(record, inventory):
    row = record.row
    name = record.table
    for field, value in tuple(row.items()):
        if not isinstance(value, Decimal):
            continue
        if (('pct' in field or field in {'avg_cpu_percent', 'avg_cpu_utilization'}) and not 0 <= value <= 100
                or field in {'uptime_h', 'runtime_h', 'active_use_h', 'runtime_h_30d'}
                and not 0 <= value <= {'uptime_h': 168, 'runtime_h_30d': 720}.get(field, 24)
                or field in {'node_count', 'query_count', 'requests', 'tokens_in', 'tokens_in_cache',
                             'tokens_out', 'licences_purchased', 'licences_active_30d', 'messages_30d',
                             'notice_period_days', 'price_per_seat', 'price_per_licence', 'network_gb',
                             'object_requests', 'accesses', 'vcpu', 'ram_gb'} and value < 0
                or field in {'eur_chf', 'usd_chf'} and value <= 0):
            record.issue('invalid_measurement', field, 'Value falls outside the documented measurement range.', 'review')
            record.set(field, None, 'invalid_measurement', 'Range validation rejected the measurement.')
    if name == 'data_platform_usage':
        nodes, runtime, active = (row.get(key) for key in ('node_count', 'runtime_h', 'active_use_h'))
        if runtime is not None and active is not None and active > runtime:
            record.issue('activity_exceeds_runtime', 'active_use_h', 'Active use exceeds runtime.', 'review')
        record.set('node_hours', nodes * runtime if nodes is not None and runtime is not None else None,
                   'derive_node_hours', 'Node count multiplied by observed runtime.')
    if name == 'server_metrics_weekly':
        asset = inventory.get(row.get('server_id'))
        kind = asset.row.get('type') if asset else None
        record.set('inventory_record_id', asset.id if asset else None, 'inventory_join', 'Unique server ID lookup.')
        if asset:
            record.set('owner_department', asset.row.get('owner_department'), 'inventory_join', 'Owner from the matched inventory record.', asset.id)
            record.set('reporting_department', asset.row.get('owner_department') or 'Unallocated',
                       'ownership_label', 'Reporting label for inventory ownership.', asset.id)
        if not asset:
            record.issue('unmatched_inventory', 'server_id', 'No unique accepted inventory record for this server.')
        if not record.raw.get('gpu_avg_pct', '').strip():
            if kind in NON_GPU_TYPES:
                record.not_applicable.add('gpu_avg_pct')
            elif kind not in GPU_TYPES:
                record.issue('unknown_gpu_applicability', 'gpu_avg_pct', 'Asset type does not establish GPU applicability.')
        avg, peak = row.get('cpu_avg_pct'), row.get('cpu_max_pct')
        if avg is not None and peak is not None and avg > peak:
            record.issue('average_above_peak', 'cpu_avg_pct', 'Weekly CPU average exceeds the peak.', 'review')
    if name == 'ai_usage':
        total, cached = row.get('tokens_in'), row.get('tokens_in_cache')
        valid = total is not None and cached is not None and cached <= total
        if total is not None and cached is not None and cached > total:
            record.issue('cache_exceeds_input', 'tokens_in_cache', 'Cached input exceeds total input.', 'review')
        record.set('uncached_input_tokens', total - cached if valid else None,
                   'derive_uncached_tokens', 'Total input less cached input when both are valid.')
    if name in CONTRACTS:
        seats, active, price, amount = (row.get(key) for key in (
            'licences_purchased', 'licences_active_30d',
            'price_per_seat' if name == 'ai_subscriptions' else 'price_per_licence', 'amount'))
        if seats is not None and active is not None and active > seats:
            record.issue('activity_exceeds_seats', 'licences_active_30d', 'Active licences exceed purchased licences.')
        if all(value is not None for value in (seats, price, amount)) and abs(seats * price - amount) > Decimal('0.01'):
            record.issue('contract_amount_discrepancy', 'amount', 'Reported monthly amount differs from seats times price.')
        if row.get('billing') not in {'annual', 'monthly'}:
            record.issue('unknown_billing_cycle', 'billing', 'Billing cycle needs confirmation.')
        if row.get('contract_status') not in {'Final', 'Draft'}:
            record.issue('unknown_contract_status', 'contract_status', 'Only documented Final versions may enter costs.', 'review')
    if name == 'business_calendar' and row.get('date'):
        day = date.fromisoformat(row['date'])
        record.set('calendar_month', day.strftime('%Y-%m'), 'calendar_fields', 'Calendar month from the recorded date.')
        record.set('calendar_quarter', f'{day.year}-Q{(day.month - 1) // 3 + 1}', 'calendar_fields', 'Calendar quarter from the recorded date.')
        record.set('weekday_iso', day.isoweekday(), 'calendar_fields', 'ISO weekday from the recorded date.')
        if (row.get('weekday') or '').casefold() != calendar.day_name[day.weekday()].casefold():
            record.issue('weekday_mismatch', 'weekday', 'Supplied weekday disagrees with the date.')
        if row.get('workday') == 1 and (day.isoweekday() > 5 or row.get('public_holiday') or row.get('company_holidays')):
            record.issue('workday_contradiction', 'workday', 'A weekend or supplied holiday is marked as a workday.')


def dates(record, field):
    row = record.row
    value = row.get(field)
    day = date.fromisoformat(value[:10]) if value else None
    if record.table == 'server_inventory':
        record.set('snapshot_date', '2026-09-06', 'inventory_snapshot', 'Inventory export as of 2026-09-06.')
        record.set('utilization_window_days', 30, 'inventory_snapshot', 'Inventory utilization covers the preceding 30 days.')
    record.set('event_date', day.isoformat() if day else None, 'reporting_date', 'Date component in the recorded timezone or local clock.')
    record.set('reporting_month', day.strftime('%Y-%m') if day else None, 'reporting_month', 'Month of the recorded date.')
    end = day
    if record.table == 'server_metrics_weekly':
        end = day + timedelta(days=6) if day else None
        record.set('week_end', end.isoformat() if end else None, 'week_end', 'Inclusive end of the full observed week.')
        if day and day.weekday() != 0:
            record.issue('invalid_week_start', 'week_start', 'Weekly observation does not start on Monday.', 'review')
    overlap = bool(day and end >= START and day <= END)
    record.set('baseline_overlap', overlap if day else None, 'baseline_scope', 'Record overlaps the inclusive baseline window.')
    if record.table == 'server_metrics_weekly':
        record.set('baseline_boundary_week', bool(overlap and (day < START or end > END)),
                   'baseline_scope', 'Boundary week retains its full measurements.')
    record.set('baseline_context', not field, 'baseline_scope', 'Undated inventory and master records provide context.')


def extract_tags(record):
    row = record.row
    if record.table == 'azure_costs':
        tags = json.loads(row['tags']) if row.get('tags') else {}
        for key, field in [('department', 'reported_department'), ('tool', 'reported_tool'),
                           ('project', 'reported_project'), ('environment', 'reported_environment')]:
            value = tags.get(key)
            if value is not None and not isinstance(value, str):
                record.issue('invalid_tag_type', field, f'Tag {key} must be a string.')
                value = None
            cleaned = value.strip() or None if value else None
            if cleaned and key == 'environment':
                cleaned = cleaned.lower()
            record.set(field, cleaned, 'azure_tag', f'Extracted {key} from Azure JSON tags.')
    elif record.table == 'aws_costs':
        for key in ('department', 'tool', 'project', 'environment'):
            record.set(f'reported_{key}', row.get(f'resource_tags_user_{key}'), 'aws_tag', f'Extracted AWS {key} tag.')
    else:
        return
    raw_project = row.get('reported_project')
    record.set('raw_reported_project', raw_project, 'raw_identifier', 'Preserve extracted provider project tag.')
    if raw_project:
        normalized = project(raw_project)
        record.set('reported_project', normalized, 'project_alias', 'Recognized project identifiers use P-NNN.')
        if normalized is None:
            record.issue('unknown_project', 'reported_project', 'Reported tag is outside the recognized project format.')
