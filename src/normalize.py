"""Build audited, versioned Silver CSVs from the thirteen Bronze exports."""
import argparse
import hashlib
import json
import re
import tempfile
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.ingest import CORE_FILES, ROOT, TEMPLATES, bronze_directory
from src.profile import END, START, read_csv
from src.silver_rules import (AGGREGATES, CONTRACTS, FREE_TEXT, USAGE,
                              classify, dates, extract_tags, metrics, project, slug)
from src.silver_storage import (REPORTS, TABLES, atomic_csv, file_hash, manifest,
                                validate, write_csv)
from src.source_specs import SPECS

AUDIT_FIELDS = ('record_id', 'source_file', 'source_row', 'field', 'original_value',
                'cleaned_value', 'rule', 'reason', 'evidence_record_id')
ISSUE_FIELDS = ('record_id', 'source_file', 'source_row', 'field', 'code', 'reason', 'impact', 'next_investigation')
META = ('record_id', 'source_file', 'source_row', 'snapshot_id', 'record_status', 'status_reason',
        'duplicate_of', 'not_applicable_fields', 'event_date', 'reporting_month', 'baseline_overlap',
        'baseline_context')
STATUSES = ('accepted', 'review', 'duplicate', 'quarantined')
REL_FIELDS = ('resource_id', 'server_id', 'record_id', 'mapping_record_id', 'evidence',
              'confidence', 'valid_from', 'valid_to', 'allocation_weight')
DERIVED_SCHEMAS = {
    'cost_facts': (*META, 'provider', 'charge_type', 'resource_id', 'cost_center', 'tool',
                   'reported_department', 'owner_department', 'consumer_department', 'reporting_department',
                   'amount_original', 'currency', 'fx_rate', 'fx_record_id', 'cost_chf', 'matched_missing_record_id',
                   'financial_status', 'baseline_eligible'),
    'usage_facts': (*META, 'usage_kind', 'resource_id', 'server_id', 'inventory_record_id',
                    'owner_department', 'consumer_department', 'reporting_department', 'region',
                    'tool', 'task_type', 'model', 'model_class', 'provider', 'project_id',
                    'node_count', 'runtime_h', 'active_use_h', 'node_hours', 'query_count',
                    'week_end', 'baseline_boundary_week', 'cpu_avg_pct', 'cpu_max_pct',
                    'ram_avg_pct', 'network_gb', 'uptime_h', 'gpu_avg_pct', 'requests',
                    'tokens_in', 'tokens_in_cache', 'tokens_out', 'uncached_input_tokens'),
    'assets': (*META, *(slug(col) for col in SPECS['server_inventory.csv'].types)),
    'contracts': (*META, *(slug(col) for name in sorted(CONTRACTS) for col in SPECS[f'{name}.csv'].types)),
    'ownership': ('association_type', 'record_id', 'source_file', 'source_row', 'snapshot_id', 'resource_id',
                  'cost_center', 'owner_department', 'reporting_department', 'association_status'),
    'resource_relationships': REL_FIELDS,
}


class Record:
    def __init__(self, table, index, raw, snapshot):
        self.table = table
        self.raw = raw
        self.id = hashlib.sha256(f'{snapshot}:{table}:{index}'.encode()).hexdigest()[:32]
        self.row = dict(record_id=self.id, source_file=f'{table}.csv', source_row=index,
                        snapshot_id=snapshot)
        self.audit = []
        self.issues = []
        self.not_applicable = set()
        self.disposition('accepted', 'Passed source disposition rules.')
        self.row['duplicate_of'] = None

    def context(self):
        return {key: self.row[key] for key in ('record_id', 'source_file', 'source_row')}

    def set(self, field, value, rule, reason, evidence=None):
        original = self.row.get(field)
        self.row[field] = value
        if original != value:
            self.audit.append(dict(**self.context(), field=field, original_value=original,
                                   cleaned_value=value, rule=rule, reason=reason,
                                   evidence_record_id=evidence))

    def disposition(self, status, reason):
        self.set('record_status', status, 'record_disposition', reason)
        self.set('status_reason', reason, 'record_disposition', reason)

    def issue(self, code, field, reason, status=None):
        self.issues.append(dict(**self.context(), field=field, code=code, reason=reason,
                                impact={'review': 'Analytical exclusion pending review',
                                        'quarantined': 'Record quarantined'}.get(status, 'Coverage or interpretation'),
                                next_investigation=investigation(code, field)))
        current = self.row['record_status']
        if status and STATUSES.index(current) < STATUSES.index(status):
            self.disposition(status, reason)


def investigation(code, field):
    if 'duplicate' in code or 'collision' in code:
        return 'Check the source grain and provider line identifiers.'
    if 'fx' in code:
        return 'Obtain one authoritative monthly exchange rate from finance.'
    if 'pool' in code or 'relationship' in code:
        return 'Request provider billing-to-instance attribution and validity evidence.'
    if 'ownership' in code or 'mapping' in code:
        return 'Confirm resource and cost-center assignments with the owner.'
    return f'Check {field or "this record"} against the source export and its owner.'


def parse_field(record, original_field, kind):
    field = slug(original_field)
    raw = record.raw[original_field]
    record.row[field] = raw
    if field in FREE_TEXT:
        return
    value = raw.strip()
    rule = 'blank_to_null'
    try:
        if not value:
            cleaned = None
        elif kind == 'number' or kind == 'binary':
            cleaned = Decimal(value)
            rule = 'parse_decimal'
            if not cleaned.is_finite() or (kind == 'binary' and cleaned not in (0, 1)):
                raise ValueError('Invalid finite or binary value')
        elif kind == 'timestamp':
            if not re.match(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', value):
                raise ValueError('Expected a date and time with second precision')
            datetime.fromisoformat(value)
            cleaned = value.replace(' ', 'T', 1)
            rule = 'parse_timestamp'
        elif kind in {'date', 'swiss_date'}:
            cleaned = datetime.strptime(value, '%d.%m.%Y' if kind == 'swiss_date' else '%Y-%m-%d').date().isoformat()
            rule = 'parse_date'
        elif kind == 'json':
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError('Tags must be a JSON object')
            cleaned, rule = raw, 'validate_json'
        elif field in {'project_id', 'project_number', 'default_project'}:
            cleaned, rule = project(value), 'project_alias'
            if cleaned is None:
                record.issue('unknown_project', field, 'Project identifier is outside the recognized P-NNN format.')
        else:
            cleaned, rule = classify(field, value)
            if field == 'tags' and record.table == 'server_inventory':
                cleaned, rule = ';'.join(part.strip() for part in value.split(';') if part.strip()) or None, 'inventory_tags'
    except (ValueError, InvalidOperation):
        cleaned, rule = None, 'invalid_value'
        record.issue('invalid_value', field, f'Value cannot be parsed as {kind}.')
    record.set(field, cleaned, rule, f'Apply the Silver {rule.replace("_", " ")} rule to {original_field}.')
    if rule in {'parse_date', 'parse_timestamp'} and raw == cleaned:
        record.audit.append(dict(**record.context(), field=field, original_value=raw, cleaned_value=cleaned,
                                 rule=rule, reason='Validated documented date representation.', evidence_record_id=None))
    if field in {'server_id', 'resource_id', 'project_id', 'project_number', 'default_project',
                 'line_item_resource_id', 'resource_tags_user_project', 'ticket_id', 'cost_center',
                 'owner_cost_center'}:
        record.row[f'raw_{field}'] = raw


def adapt(table, index, raw, snapshot):
    record = Record(table, index, raw, snapshot)
    spec = SPECS[f'{table}.csv']
    for field, kind in spec.types.items():
        parse_field(record, field, kind)
    dates(record, slug(spec.date))
    row = record.row
    if table in {'server_inventory', 'server_metrics_weekly', 'mapping_departments_tools',
                 'data_platform_usage', 'it_tickets'}:
        identity = 'ticket_id' if table == 'it_tickets' else slug(spec.resource)
        if not row.get(identity):
            record.issue('missing_grain_identifier', identity, 'The required source identifier is missing.', 'quarantined')
    if spec.date and row.get('event_date') is None:
        record.issue('missing_event_date', slug(spec.date), 'No valid date for the documented source grain.', 'quarantined')
    if spec.cadence == 'monthly' and row.get('event_date') and not row['event_date'].endswith('-01'):
        record.issue('invalid_month_start', slug(spec.date), 'Monthly records must use the first day of the month.', 'review')
    if table in {'azure_costs', 'aws_costs'}:
        field = slug(spec.resource)
        path = row.get(field)
        if table == 'azure_costs':
            suffix = path.rstrip('/').rsplit('/', 1)[-1] if path else None
            record.set('provider', 'Azure', 'provider_source', 'Provider identified by the export.')
        else:
            suffix = path.rsplit(':', 1)[-1].rsplit('/', 1)[-1] if path else None
            record.set('provider', 'AWS', 'provider_source', 'Provider identified by the export.')
            monthly = row.get('pricing_unit') == 'month'
            record.set('observation_cadence', 'monthly' if monthly else 'daily', 'aws_cadence',
                       'Month-unit fees are monthly observations.')
            record.set('charge_category', 'usage' if row.get('line_item_line_item_type') == 'Usage' else 'fee',
                       'aws_charge_type', 'Usage lines are distinguished from provider fees.')
        record.set('resource_path', raw[spec.resource], 'provider_resource', 'Complete provider resource reference.')
        record.set('resource_id', suffix.casefold() if suffix else None, 'provider_resource', 'Resource suffix from provider reference.')
        extract_tags(record)
        if not row.get('resource_id'):
            record.issue('missing_resource', 'resource_id', 'Provider reference has no usable resource identifier.')
        if table == 'azure_costs' and row.get('charge_type') not in {'Usage', 'Credit'}:
            record.issue('unknown_charge_type', 'charge_type', 'Charge classification needs provider confirmation.')
        if table == 'aws_costs' and row.get('line_item_line_item_type') not in {'Usage', 'Fee'}:
            record.issue('unknown_charge_type', 'line_item_line_item_type', 'Charge classification needs provider confirmation.')
    for value, applies in (
        ('avg_cpu_percent', row.get('unit_of_measure') in {'vCore-hour', 'vCPU-hour', 'GPU-hour', 'node-hour'}),
        ('avg_cpu_utilization', row.get('pricing_unit') == 'vCPU-hour'),
        ('object_requests', row.get('pricing_unit') == 'GB-day'),
        ('accesses', row.get('service') == 'Storage'),
    ):
        raw_value = next((record.raw[field] for field in spec.types if slug(field) == value), None)
        if raw_value is not None and not raw_value.strip() and not applies:
            record.not_applicable.add(value)
    if table == 'ai_usage':
        record.set('consumer_department', row.get('department'), 'consumer_ownership', 'Department consuming the AI service.')
    if table != 'server_metrics_weekly':
        metrics(record, {})
    return record


def source_key(record, raw=False):
    table = record.table
    fields = SPECS[f'{table}.csv'].key.split()
    if raw:
        return tuple(record.raw[field] for field in fields)
    return tuple(record.row.get(slug(field)) for field in fields)


def resolve_collisions(records):
    seen = {}
    groups = defaultdict(list)
    for record in records:
        signature = tuple(record.raw.values())
        first = seen.setdefault(signature, record)
        if first is not record and record.table in AGGREGATES:
            record.disposition('duplicate', 'Exact raw repeat at documented aggregate grain.')
            record.set('duplicate_of', first.id, 'duplicate_exclusion', 'Retain the first logical source row.', first.id)
        else:
            candidate = source_key(record)
            if record.table in {'azure_costs', 'aws_costs'}:
                period = record.row['reporting_month'] if record.row.get('observation_cadence') == 'monthly' else record.row['event_date']
                candidate = (record.row.get('resource_id'), period, *candidate[2:])
            groups[candidate].append(record)
    for group in groups.values():
        if len(group) < 2:
            continue
        # At the documented aggregate grain, an exact priced mirror can
        # resolve the omitted value without adding a second charge.
        if len(group) == 2 and group[0].table in {'azure_costs', 'aws_costs'}:
            first, second = group
            amount_field = SPECS[f'{first.table}.csv'].amount
            amount_key = slug(amount_field)
            same_line = all(first.raw[field] == second.raw[field] for field in first.raw if field != amount_field)
            recorded = [r for r in group if r.row.get(amount_key) is not None]
            missing = [r for r in group if not r.raw[amount_field].strip()]
            if same_line and len(recorded) == len(missing) == 1 and all(
                r.row['record_status'] == 'accepted' for r in group
            ):
                priced, incomplete = recorded[0], missing[0]
                incomplete.disposition('duplicate', 'Exact billing mirror with the amount present on its counterpart.')
                incomplete.set('duplicate_of', priced.id, 'recover_recorded_charge',
                               'Count the verified charge once using its priced source row.', priced.id)
                priced.set('matched_missing_record_id', incomplete.id, 'recover_recorded_charge',
                           'This priced line resolves the otherwise identical missing-amount mirror.', incomplete.id)
                continue
        raw_keys = {source_key(record, raw=True) for record in group}
        identical = len({tuple(record.raw.values()) for record in group}) == 1
        code = ('normalized_key_collision' if len(raw_keys) > 1 else
                'exact_duplicate_candidate' if identical else 'key_collision')
        for record in group:
            record.issue(code, 'candidate_key', f'{len(group)} retained records share the candidate key.', 'review')


def unique(records, field):
    groups = defaultdict(list)
    for record in records:
        key = record.row.get(field)
        if key and record.row['record_status'] != 'duplicate':
            groups[key].append(record)
    return {key: group[0] for key, group in groups.items()
            if len(group) == 1 and group[0].row['record_status'] == 'accepted'}


def enrich(tables):
    mapping = tables['mapping_departments_tools']
    resources = unique(mapping, 'resource_id')
    labels = unique(mapping, 'tool')
    inventory = unique(tables['server_inventory'], 'server_id')
    departments = defaultdict(set)
    for record in resources.values():
        center, department = (record.row.get(field) for field in ('cost_center', 'department'))
        if center and department:
            departments[center].add(department)
    for records in tables.values():
        for record in records:
            row, table = record.row, record.table
            if table == 'hoster_invoice':
                mapped = labels.get(row.get('item'))
                record.set('provider', 'Swiss Hoster', 'provider_source', 'Provider identified by the export.')
                record.set('resource_id', mapped.row['resource_id'] if mapped else None,
                           'mapping_tool_join', 'Resource matched by a unique invoice item label.', mapped.id if mapped else None)
                if not mapped:
                    record.issue('unmatched_item', 'item', 'No unique tool mapping matches the invoice label.')
            if table not in {'azure_costs', 'aws_costs', 'hoster_invoice', 'ai_usage',
                             'data_platform_usage', 'server_inventory', *CONTRACTS}:
                continue
            resource = row.get('resource_id')
            mapped = resources.get(resource)
            if resource and not mapped:
                record.issue('unmatched_resource', 'resource_id', 'No unique accepted resource ownership mapping.')
            center = row.get('cost_center') or row.get('owner_cost_center')
            mapped_center = mapped.row.get('cost_center') if mapped else None
            evidence = mapped.id if mapped else next(
                (item.id for item in resources.values() if center and item.row.get('cost_center') == center
                 and item.row.get('department') in departments.get(center, set())), None)
            candidates = departments.get(center, set())
            owner = mapped.row.get('department') if mapped else next(iter(candidates)) if len(candidates) == 1 else None
            if center and mapped_center and center != mapped_center:
                record.issue('ownership_conflict', 'cost_center', 'Reported cost center differs from resource mapping.')
                owner = None
            elif not mapped and center and len(candidates) > 1:
                record.issue('ambiguous_ownership', 'cost_center', 'Cost center has multiple department associations.')
            if not center and mapped_center:
                record.set('cost_center', mapped_center, 'mapping_enrichment', 'Cost center from unique resource mapping.', evidence)
            record.set('owner_department', owner, 'mapping_enrichment', 'Ownership from unique resource or cost-center evidence.', evidence)
            record.set('reporting_department', owner or 'Unallocated', 'ownership_label', 'Display label for unresolved ownership.')
            if not owner:
                record.issue('unresolved_ownership', 'owner_department', 'No unambiguous owner department is available.')
            if mapped:
                for field in ('tool', 'environment', 'criticality'):
                    record.set(f'mapped_{field}', mapped.row.get(field), 'mapping_enrichment', 'Attribute from unique resource mapping.', evidence)
                record.set('suggested_project', mapped.row.get('default_project'), 'mapping_enrichment',
                           'Default project suggestion from master data.', evidence)
    for record in tables['server_metrics_weekly']:
        metrics(record, inventory)
    known_ids = set(resources) | set(inventory)
    pattern = re.compile(r'(?<![\w-])(?:' + '|'.join(map(re.escape, sorted(known_ids))) + r')(?![\w-])', re.IGNORECASE) if known_ids else None
    for record in tables['it_tickets']:
        row = record.row
        text = f"{row.get('title') or ''} {row.get('description') or ''}"
        mentions = sorted({match.casefold() for match in pattern.findall(text)}) if pattern else []
        record.set('resource_mentions', ';'.join(mentions) or None, 'ticket_mentions',
                   'Whole-token matches against accepted resource and inventory IDs.')
        resource = row.get('resource_id')
        if (resource and resource not in known_ids) or (mentions and set(mentions) != {resource}):
            record.issue('ticket_scope_review', 'resource_id', 'Structured reference and known text mentions require scope review.')
    for mapping_record in mapping:
        row = mapping_record.row
        center = row.get('cost_center')
        if len(departments.get(center, ())) > 1:
            mapping_record.issue('ambiguous_ownership', 'cost_center', 'Cost center maps to more than one department.')
        if not row.get('department'):
            mapping_record.issue('unresolved_ownership', 'department', 'Master record has no recorded department.')
    return resources, inventory, departments


def relationships(resources, inventory, source_records):
    rows = []
    billed = defaultdict(list)
    for record in source_records:
        if record.row.get('resource_id'):
            billed[record.row['resource_id']].append(record)
    for resource, server in sorted({**{r: r for r in billed if r in inventory}, 'gpu-ml': 'gpu-ml-01'}.items()):
        asset, mapping = inventory.get(server), resources.get(resource)
        if not asset or resource not in billed:
            continue
        exact = server == resource and all(
            record.row.get('provider') == asset.row.get('provider') for record in billed[resource])
        rows.append(dict(resource_id=resource, server_id=server, record_id=asset.id,
                         mapping_record_id=mapping.id if mapping else None,
                         evidence='Identical provider and resource identifiers' if exact else
                         (f'Candidate only: billed {resource} and inventory {server}; '
                          f"asset type {asset.row.get('type')}, project {asset.row.get('project_id')}, "
                          f"provider {asset.row.get('provider')}; no explicit billing-to-instance link"),
                         confidence='high' if exact else 'candidate'))
        if not exact:
            billed[resource][0].issue('unverified_asset_relationship', 'resource_id',
                                      f'Confirm that billed {resource} refers to inventory {server}.')
    if 'vm-test' in billed:
        mapping = resources.get('vm-test')
        rows.append(dict(resource_id='vm-test', server_id=None, mapping_record_id=mapping.id if mapping else None,
                         evidence='Pool label; no documented member list or allocation weights', confidence='unresolved'))
        billed['vm-test'][0].issue('unresolved_billing_pool', 'resource_id',
                                  'vm-test is billed as a pool; member identities and weights are unknown.')
    return rows


def financial_facts(tables):
    rates = unique(tables['exchange_rates'], 'reporting_month')
    facts = []
    for table, records in tables.items():
        spec = SPECS[f'{table}.csv']
        if not spec.amount:
            continue
        for record in records:
            row = record.row
            amount = row.get(slug(spec.amount))
            currency = 'CHF' if spec.currency == 'CHF' else row.get(slug(spec.currency))
            month = row.get('reporting_month')
            fx_record = rates.get(month) if currency in {'EUR', 'USD'} else None
            rate = Decimal(1) if currency == 'CHF' else fx_record.row.get(f'{currency.lower()}_chf') if fx_record else None
            cost = amount * rate if amount is not None and rate is not None else None
            record.set('amount_original', amount, 'financial_source_amount', 'Recorded source amount in original currency.')
            record.set('original_currency', currency, 'financial_source_currency', 'Recorded currency or CHF from source schema.')
            record.set('fx_rate', rate, 'monthly_fx', 'CHF per unit of source currency; CHF identity factor is 1.',
                       fx_record.id if fx_record else None)
            record.set('converted_cost_chf', cost, 'convert_chf', 'Source amount multiplied by the unrounded monthly FX factor.',
                       fx_record.id if fx_record else None)
            record.set('fx_record_id', fx_record.id if fx_record else None, 'monthly_fx', 'Exchange-rate evidence record.')
            if amount is None:
                record.issue('missing_amount', spec.amount, 'Source amount is unknown.')
            if rate is None:
                record.issue('missing_or_ambiguous_fx', 'fx_rate', 'No valid unique rate for this currency and month.')
            status = row['record_status']
            if status == 'accepted':
                if table in CONTRACTS and row.get('contract_status') != 'Final':
                    status = 'draft'
                elif not row['baseline_overlap']:
                    status = 'outside_baseline'
                elif amount is None:
                    status = 'missing_amount'
                elif rate is None:
                    status = 'missing_fx'
                else:
                    status = 'included'
            record.set('financial_status', status, 'financial_disposition', 'Baseline treatment from disposition, dates, amount and FX.')
            record.set('baseline_eligible', status in {'included', 'missing_amount', 'missing_fx'},
                       'financial_disposition', 'Accepted in-window charges and Final contract versions are eligible.')
            facts.append(dict(
                **{field: row.get(field) for field in META}, provider=row.get('provider'),
                charge_type=row.get('charge_type') or row.get('line_item_line_item_type') or
                ('Contract' if table in CONTRACTS else 'Gateway' if table == 'ai_usage' else 'Invoice'),
                resource_id=row.get('resource_id'), cost_center=row.get('cost_center'),
                tool=row.get('reported_tool') or row.get('tool') or row.get('mapped_tool'),
                **{field: row.get(field) for field in ('reported_department', 'owner_department',
                                                       'consumer_department', 'reporting_department')},
                amount_original=amount, currency=currency, fx_rate=rate,
                fx_record_id=fx_record.id if fx_record else None, cost_chf=cost,
                matched_missing_record_id=row.get('matched_missing_record_id'),
                financial_status=status, baseline_eligible=row['baseline_eligible']))
    return facts


def source_hashes(data):
    data = bronze_directory(data)
    return [{'name': name, 'sha256': file_hash(data / name)} for name in (*CORE_FILES, *TEMPLATES)]


def build(data, out):
    data = bronze_directory(data)
    from src.silver_profiles import PROFILE_FIELDS, profiles

    hashes = source_hashes(data)
    snapshot = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    rules = hashlib.sha256(''.join(file_hash(ROOT / 'src' / f'{module}.py') for module in
                                  ('normalize', 'reconciliation', 'silver_rules', 'silver_storage',
                                   'silver_profiles', 'source_specs', 'profile')).encode()).hexdigest()
    version = hashlib.sha256(f'{snapshot}:{rules}'.encode()).hexdigest()
    tables = {}
    for name in CORE_FILES:
        table = Path(name).stem
        _, rows = read_csv(data / name, SPECS[name].types)
        tables[table] = [adapt(table, index, raw, snapshot) for index, raw in enumerate(rows, 2)]
        resolve_collisions(tables[table])
    resources, inventory, departments = enrich(tables)
    relationships_rows = relationships(resources, inventory, tables['azure_costs'] + tables['aws_costs'] + tables['hoster_invoice'])
    facts = financial_facts(tables)
    records = [record for group in tables.values() for record in group]
    measured = {
        'data_platform_usage': ('node_count', 'runtime_h', 'active_use_h', 'query_count'),
        'server_inventory': ('cpu_utilisation_30d_pct', 'ram_utilisation_30d_pct', 'runtime_h_30d'),
        'server_metrics_weekly': ('cpu_avg_pct', 'cpu_max_pct', 'ram_avg_pct', 'uptime_h', 'gpu_avg_pct'),
        'ai_usage': ('requests', 'tokens_in', 'tokens_in_cache', 'tokens_out'),
        'azure_costs': ('avg_cpu_percent',), 'aws_costs': ('avg_cpu_utilization', 'object_requests'),
        'exchange_rates': ('eur_chf', 'usd_chf'),
    }
    for record in records:
        for field in measured.get(record.table, ()):
            if record.row.get(field) is None and field not in record.not_applicable:
                record.issue('missing_measurement', field, 'Applicable measurement is unavailable.')
    for record in records:
        record.set('not_applicable_fields', ';'.join(sorted(record.not_applicable)) or None,
                   'measurement_applicability', 'Blank measures established as not applicable.')
    record_index = {record.id: record for record in records}
    for fact in facts:
        fact['not_applicable_fields'] = record_index[fact['record_id']].row['not_applicable_fields']
    report, extra_issues = profiles(tables)
    center_rows = {}
    for key, record in resources.items():
        center, department = (record.row.get(field) for field in ('cost_center', 'department'))
        if center:
            center_rows.setdefault((center, department), dict(
                association_type='cost_center_department', **record.context(), snapshot_id=snapshot,
                cost_center=center, owner_department=department, reporting_department=department or 'Unallocated',
                association_status='ambiguous' if len(departments[center]) > 1 else
                'documented' if department else 'unresolved'))
    derived = dict(
        cost_facts=facts,
        usage_facts=[dict({key: record.row.get(key) for key in DERIVED_SCHEMAS['usage_facts']},
                          usage_kind=name) for name in tables if name in USAGE for record in tables[name]],
        assets=[record.row for record in tables['server_inventory']],
        contracts=[record.row for name in tables if name in CONTRACTS for record in tables[name]],
        ownership=[dict(association_type='resource', **record.context(), snapshot_id=snapshot, resource_id=key,
                        cost_center=record.row.get('cost_center'), owner_department=record.row.get('department'),
                        reporting_department=record.row.get('department') or 'Unallocated',
                        association_status='ambiguous' if len(departments.get(record.row.get('cost_center'), ())) > 1
                        else 'unresolved' if not record.row.get('department') else 'documented')
                   for key, record in resources.items()] + list(center_rows.values()),
        resource_relationships=relationships_rows,
    )
    if hashes != source_hashes(data):
        raise ValueError('Bronze changed during Silver generation')
    staging = out / '.silver-staging'
    staging.mkdir(parents=True, exist_ok=True)
    destination = staging / version
    with tempfile.TemporaryDirectory(dir=staging) as temp:
        directory = Path(temp) / version
        directory.mkdir()
        for name, group in tables.items():
            write_csv(directory / f'{name}.csv', [record.row for record in group],
                      (*META, *(slug(col) for col in SPECS[f'{name}.csv'].types)))
        for name, rows in derived.items():
            write_csv(directory / f'{name}.csv', rows, DERIVED_SCHEMAS[name])
        write_csv(directory / 'transformation_log.csv', [entry for record in records for entry in record.audit], AUDIT_FIELDS)
        write_csv(directory / 'profiles.csv', report, PROFILE_FIELDS)
        write_csv(directory / 'unresolved_issues.csv', [entry for record in records for entry in record.issues] + extra_issues, ISSUE_FIELDS)
        manifest(directory, version, snapshot, rules, (*TABLES, *REPORTS))
        validate(directory, version, (*TABLES, *REPORTS))
        if destination.exists():
            validate(destination, version, (*TABLES, *REPORTS))
            if file_hash(directory / 'manifest.csv') != file_hash(destination / 'manifest.csv'):
                raise ValueError('Silver generation is not deterministic')
        else:
            directory.rename(destination)
    atomic_csv(out / 'pending_silver.csv', [{'version': version}])
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    print(build(args.data, args.out))


if __name__ == '__main__':
    main()
