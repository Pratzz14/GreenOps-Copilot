"""Reconcile activity only after aggregating each source to the comparison grain."""
from collections import defaultdict
from decimal import Decimal

from src.silver_rules import project

COMPARISON_FIELDS = ('comparison', 'reporting_month', 'entity', 'unit', 'extra_quantity',
                     'core_quantity', 'difference', 'core_to_extra_ratio', 'extra_rows', 'core_rows',
                     'baseline_overlap', 'basis', 'interpretation')
# Subtract only reconciliations with a common unit and a comparable scope.
BASIS = {'ai_tokens': 'same_unit', 'ci_runtime': 'same_unit', 'web_volume': 'same_unit',
         'provider_spend': 'same_unit', 'ai_agent_tokens': 'overlapping_activity',
         'powerbi_capacity': 'cross_unit', 'allocation_cost_per_fte': 'allocation_view',
         'allocation_cost_per_project_hour': 'allocation_view'}
CLOUD = ('Azure', 'AWS', 'Swiss Hoster')
SPEND_SCOPES = {
    'Azure': lambda row: row['provider'] == 'Azure',
    'AWS': lambda row: row['provider'] == 'AWS',
    'Azure + AWS': lambda row: row['provider'] in CLOUD[:2],
    'Azure + AWS + Swiss Hoster': lambda row: row['provider'] in CLOUD,
    'Cloud, hoster and AI gateway': lambda row: row['provider'] in CLOUD or row['source_file'] == 'ai_usage.csv',
    'All recorded charges': lambda row: True,
}
RATIO = Decimal('0.000001')


def enrich_extras(tables, resources):
    projects = {record.row['project_id'] for record in tables['projects']
                if record.row['record_status'] == 'accepted'}
    for group in tables.values():
        for record in group:
            if record.table in {'log_volume', 'ai_agent_runs', 'ci_pipeline_runs',
                                'data_catalog_tables', 'project_hours_monthly'}:
                value = project(record.row.get('project_id') or '')
                record.set('verified_project_id', value if value in projects else None,
                           'project_master', 'Match canonical spelling against the project master.')
    for record in tables['powerbi_usage']:
        owner = resources.get(record.row.get('resource_id'))
        if owner:
            record.set('owner_department', owner.row.get('department'), 'report_owner',
                       'Exact resource match to the ownership master.', owner.id)
    for record in tables['data_platform_jobs']:
        owner = resources.get(record.row.get('resource_id'))
        if owner:
            record.set('owner_department', owner.row.get('department'), 'job_resource',
                       'Exact resource match to the ownership master.', owner.id)
        else:
            record.issue('unmatched_resource', 'resource_id', 'The job resource is absent from the ownership master.')
    used = {(provider, record.row.get(field)) for provider, table, field in (
        ('AWS', 'aws_costs', 'product_region'), ('Azure', 'azure_costs', 'resource_location'))
            for record in tables[table] if record.row['record_status'] == 'accepted'}
    for record in tables['data_center_locations']:
        row = record.row
        if (row['provider'], row['region']) in used and str(row['used_by_sme']).casefold() == 'no':
            record.issue('billing_location_conflict', 'used_by_sme',
                         'Accepted provider billing shows usage in this region. Use billing geography for those records.')


def comparisons(tables, facts):
    totals = defaultdict(lambda: [None, None, 0, 0])
    notes = {
        'ai_tokens': 'Invoice and gateway scope may differ. Agent logs and gateway records lack a verified run-level '
                     'match, so the agent logs cannot explain the excess.',
        'ai_agent_tokens': 'Agent and gateway token volumes matched by month, provider and model class. '
                           'The ratio is gateway tokens divided by agent tokens. Potential overlap precludes adding the totals.',
        'ci_runtime': 'Logged run duration against billed runner-minutes.',
        'web_volume': 'Compare Zurich dates present on both sides. Volume agreement does not prove identical network scope.',
        'allocation_cost_per_fte': 'Allocation view. Recorded department CHF per FTE. The ledger is not re-allocated.',
        'allocation_cost_per_project_hour': 'Allocation view. Recorded department CHF per booked project hour. '
                                            'The ledger is not re-allocated.',
    }
    specific = {}

    def add(name, month, entity, unit, value, side):
        group = totals[name, month, entity, unit]
        if value is not None:
            group[side] = (group[side] or Decimal(0)) + value
            group[side + 2] += 1

    def accepted(table):
        return (record.row for record in tables[table]
                if record.row['record_status'] == 'accepted' and record.row['baseline_overlap'])

    classes = defaultdict(set)
    for side, table in enumerate(('ai_invoice_monthly', 'ai_usage')):
        for row in accepted(table):
            entity = f"{row.get('provider')} / {row.get('model_class')}"
            if side and row.get('model_class'):
                classes[row['reporting_month'], row.get('provider'), row.get('model')].add(row['model_class'])
            for field in ('tokens_in', 'tokens_out'):
                add('ai_tokens', row['reporting_month'], entity, field, row.get(field), side)
                if side:
                    add('ai_agent_tokens', row['reporting_month'], entity, field, row.get(field), 1)
    for row in accepted('ai_agent_runs'):
        matches = classes[row['reporting_month'], row.get('provider'), row.get('model')]
        model_class = next(iter(matches)) if len(matches) == 1 else "ambiguous model" if matches else "unmatched model"
        entity = f"{row.get('provider')} / {model_class}"
        for field in ('tokens_in', 'tokens_out'):
            add('ai_agent_tokens', row['reporting_month'], entity, field, row.get(field), 0)
    # Gateway groups without agent activity carry no share.
    for key in [key for key, group in totals.items() if key[0] == 'ai_agent_tokens' and group[0] is None]:
        del totals[key]

    unlogged = defaultdict(int)
    for row in accepted('ci_pipeline_runs'):
        duration = row.get('duration_seconds')
        if row.get('region') and duration is not None:
            add('ci_runtime', row['reporting_month'], row['region'], 'runner-minute', duration / 60, 0)
        elif row.get('region'):
            unlogged[row['reporting_month'], row['region']] += 1
    for row in accepted('aws_costs'):
        if row.get('pricing_unit') == 'runner-minute' and row.get('charge_category') == 'usage':
            add('ci_runtime', row['reporting_month'], row['product_region'], 'runner-minute',
                row.get('line_item_usage_amount'), 1)

    web = list(accepted('web_traffic'))
    billed = [row for row in accepted('hoster_invoice') if row.get('service') == 'Web hosting/CDN']
    common = {row['event_date'] for row in web} & {row['event_date'] for row in billed}
    for side, (rows, field) in enumerate(((web, 'expanded_gb'), (billed, 'quantity'))):
        for row in rows:
            if row['event_date'] in common and (side == 0 or row.get('unit') == 'GB'):
                add('web_volume', row['reporting_month'], 'Swiss Hoster', 'GB', row.get(field), side)

    included = [row for row in facts if row['baseline_eligible'] and row['financial_status'] == 'included']
    for row in accepted('provider_monthly_report'):
        for scope in SPEND_SCOPES:
            add('provider_spend', row['reporting_month'], scope, 'CHF', row['total_cost_chf'], 0)
    for row in included:
        for scope, member in SPEND_SCOPES.items():
            if member(row):
                add('provider_spend', row['reporting_month'], scope, 'CHF', row['cost_chf'], 1)
    gaps = {}
    for scope in SPEND_SCOPES:
        months = [group for key, group in totals.items() if key[0] == 'provider_spend' and key[2] == scope
                  and group[0] is not None and group[1] is not None]
        reported = sum(group[0] for group in months)
        if months and reported:
            gaps[scope] = sum(abs(group[0] - group[1]) for group in months) / reported
    closest = min(gaps, key=gaps.get) if gaps else None
    for scope, gap in gaps.items():
        text = f'Tested scope. Mean absolute gap {gap:.1%} of the report across compared months.'
        if scope == closest:
            text = (f'Closest tested scope. Mean absolute gap {gap:.1%} of the report across compared months. '
                    + ('It reconciles within 1%.' if gap <= Decimal('0.01') else
                       'No tested scope reconciles within 1%, so the report scope stays unresolved.'))
        specific['provider_spend', scope] = text + ' The comparison is diagnostic and stays outside the ledger.'

    daily = set()
    for row in accepted('powerbi_usage'):
        add('powerbi_capacity', row['reporting_month'], 'pbi-kap', 'refresh-minute per capacity-day',
            row.get('refresh_duration_min'), 0)
    for row in accepted('azure_costs'):
        if (row.get('resource_id') == 'pbi-kap' and row.get('charge_type') == 'Usage'
                and (row.get('unit_of_measure') or '').casefold() == 'capacity-day'):
            add('powerbi_capacity', row['reporting_month'], 'pbi-kap', 'refresh-minute per capacity-day',
                row.get('quantity'), 1)
            daily.add(row.get('quantity'))
    notes['powerbi_capacity'] = (
        f'Billed quantity is {next(iter(daily))} capacity-day per observed billing record. '
        'Estimate an electricity reduction only after verifying that refresh changes reduce attributable compute or capacity.'
        if len(daily) == 1 and None not in daily else
        'Billed capacity varies or is incomplete. Its relationship to refresh activity is unverified.')

    for row in accepted('headcount'):
        add('allocation_cost_per_fte', row['reporting_month'], row.get('department'), 'CHF per FTE', row.get('fte'), 0)
    for row in accepted('project_hours_monthly'):
        add('allocation_cost_per_project_hour', row['reporting_month'], row.get('department'),
            'CHF per project hour', row.get('hours'), 0)
    for row in included:
        for name, unit in (('allocation_cost_per_fte', 'CHF per FTE'),
                           ('allocation_cost_per_project_hour', 'CHF per project hour')):
            add(name, row['reporting_month'], row['reporting_department'] or 'Unallocated', unit, row['cost_chf'], 1)

    result = []
    for (name, month, entity, unit), (extra, core, extra_rows, core_rows) in sorted(
            totals.items(), key=lambda item: tuple(str(part) for part in item[0])):
        both = extra is not None and core is not None
        note = specific.get((name, entity), notes.get(name))
        if name == 'ci_runtime' and unlogged[month, entity]:
            note += f' {unlogged[month, entity]} accepted runs have no logged duration and are absent from the logged total.'
        result.append(dict(
            comparison=name, reporting_month=month, entity=entity, unit=unit,
            extra_quantity=extra, core_quantity=core,
            difference=extra - core if both and BASIS[name] == 'same_unit' else None,
            core_to_extra_ratio=(core / extra).quantize(RATIO) if both and extra else None,
            extra_rows=extra_rows, core_rows=core_rows, baseline_overlap=True, basis=BASIS[name],
            interpretation=note))
    return result
