"""Phase 3 disposition, reproducibility, precision and API contracts."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from src.ingest import CORE_FILES, ROOT, TEMPLATES, snapshot
from src.normalize import adapt, build, financial_facts, resolve_collisions, source_hashes
from src.profile import read_csv
from src.reconciliation import publish, reconcile
from src.silver_storage import SOURCE_TABLES, write_csv


def adapted(table, index=2, **overrides):
    _, rows = read_csv(ROOT / 'data' / 'bronze' / f'{table}.csv')
    return adapt(table, index, {**rows[0], **overrides}, 'test')


def test_source_adapters_preserve_grain_and_parse_source_values():
    records = {table: adapted(table) for table in SOURCE_TABLES}
    assert all(record.row['source_row'] == 2 for record in records.values())
    assert records['hoster_invoice'].row['date'] == '2024-11-01'
    assert records['azure_costs'].row['resource_id'] == 'db-fin'
    assert records['azure_costs'].row['reported_project'] == 'P-015'
    assert records['aws_costs'].row['line_item_usage_start_date'] == '2024-11-01T00:00:00'
    assert records['aws_costs'].row['resource_id'] == 'cicd'
    assert records['data_platform_usage'].row['node_hours'] == 192
    assert records['server_inventory'].row['snapshot_date'] == '2026-09-06'
    assert records['server_inventory'].row['utilization_window_days'] == 30
    assert records['ai_usage'].row['uncached_input_tokens'] == 749398
    assert records['business_calendar'].row['weekday_iso'] == 5
    assert records['exchange_rates'].row['eur_chf'] == Decimal('0.9355')
    ticket = adapted('it_tickets', description='  line 1\nline 2  ', project_id='unused')
    assert ticket.row['description'] == '  line 1\nline 2  '
    hoster = adapted('hoster_invoice', ProjectNumber=' p001 ', Amount_CHF='')
    assert hoster.row['project_number'] == 'P-001'
    assert hoster.row['raw_project_number'] == ' p001 '
    assert hoster.row['amount_chf'] is None


def test_exact_duplicates_collisions_and_contract_versions():
    original = adapted('data_platform_usage')
    duplicate = adapted('data_platform_usage', 3)
    collision = adapted('data_platform_usage', 4, resource_id=' DP-DEV ', runtime_h='20')
    resolve_collisions([original, duplicate, collision])
    assert duplicate.row['duplicate_of'] == original.id
    assert duplicate.row['record_status'] == 'duplicate'
    assert collision.row['record_status'] == original.row['record_status'] == 'review'
    assert any(issue['code'] == 'normalized_key_collision' for issue in collision.issues)

    final = adapted('saas_contracts', month='2026-03-01')
    draft = adapted('saas_contracts', 3, month='2026-03-01', contract_status='Draft')
    resolve_collisions([final, draft])
    facts = financial_facts({'exchange_rates': [], 'saas_contracts': [final, draft]})
    assert [fact['financial_status'] for fact in facts] == ['included', 'draft']
    assert facts[0]['cost_chf'] == Decimal('380')


def test_fx_credit_zero_missing_and_decimal_reconciliation():
    def charge(index, amount, currency='EUR'):
        return adapted('azure_costs', index, Date='2026-03-04', CostInBillingCurrency=amount,
                       BillingCurrency=currency, ChargeType='Credit')
    records = [charge(2, '-3.0001'), charge(3, '0', 'CHF'), charge(4, ''), charge(5, '4', 'USD')]
    rate = adapted('exchange_rates', month='2026-03-01', eur_chf='0.91234', usd_chf='')
    facts = financial_facts({'exchange_rates': [rate], 'azure_costs': records})
    assert facts[0]['cost_chf'] == Decimal('-2.737111234')
    assert facts[0]['fx_record_id'] == rate.id
    assert facts[1]['cost_chf'] == 0
    assert facts[2]['cost_chf'] is None and facts[2]['financial_status'] == 'missing_amount'
    assert facts[3]['cost_chf'] is None and facts[3]['financial_status'] == 'missing_fx'
    csv_facts = [{key: '' if value is None else str(value) for key, value in fact.items()} for fact in facts]
    total, *grouped = reconcile(csv_facts)
    assert total['recorded_cost_chf'] == Decimal('-2.737111234')
    assert total['coverage_status'] == 'incomplete'
    assert all(row['agrees_with_total'] for row in grouped)


def test_period_context_and_timestamp_precision():
    aws = adapted('aws_costs', pricing_unit='MONTH', line_item_line_item_type='Fee',
                  line_item_usage_start_date='2025-09-01 12:10:00.123456789')
    assert aws.row['observation_cadence'] == 'monthly'
    assert aws.row['line_item_usage_start_date'] == '2025-09-01T12:10:00.123456789'
    assert aws.row['charge_category'] == 'fee'
    week = adapted('server_metrics_weekly', week_start='2026-08-31')
    assert week.row['week_end'] == '2026-09-06'
    assert week.row['baseline_boundary_week']
    assert week.row['uptime_h'] == 168


@pytest.fixture
def build_small(tmp_path):
    data, out = tmp_path / 'data', tmp_path / 'out'
    data.mkdir()
    for name in CORE_FILES:
        columns, rows = read_csv(ROOT / 'data' / 'bronze' / name)
        write_csv(data / name, rows[:2], columns)
    for name in TEMPLATES:
        (data / name).write_bytes((ROOT / 'data' / 'bronze' / name).read_bytes())
    hashes = source_hashes(data)
    snapshot(data, out)
    version = build(data, out)
    assert not (out / 'current_silver.csv').exists()
    assert publish(out) == version
    return data, out, version, hashes


def test_round_trip_determinism_lineage_and_api_filters(build_small, tmp_path):
    data, out, version, hashes = build_small
    directory = out / 'silver' / version
    before = (directory / 'manifest.csv').read_bytes()
    assert build(data, out) == publish(out) == version
    assert (directory / 'manifest.csv').read_bytes() == before
    assert source_hashes(data) == hashes
    with TestClient(create_app(out, tmp_path / 'dist')) as client:
        base = '/api/v1/silver'
        overview = client.get(base).json()
        assert overview['version'] == version
        assert len(overview['tables']) == 19
        by_name = {item['table']: item for item in overview['tables']}
        assert by_name['azure_costs']['transformations']['provider_resource'] > 0
        total = 0
        for name in CORE_FILES:
            _, rows = read_csv(directory / name)
            assert [int(row['source_row']) for row in rows] == [2, 3]
            total += len(rows)
        assert total == sum(overview[key] for key in ('accepted', 'review', 'duplicates', 'quarantined'))
        response = client.get(base + '/tables/azure_costs/rows', params={'limit': 1, 'offset': 1, 'version': version})
        page = response.json()
        assert page['total'] == 2 and page['items'][0]['source_row'] == 3
        key = page['items'][0]['record_id']
        lineage = client.get(base + f'/records/{key}').json()
        assert lineage['version'] == version
        assert any(change['rule'] == 'provider_resource' for change in lineage['changes'])
        profile = client.get(base + '/tables/azure_costs/profile').json()
        labels = {item['label'] for item in profile['items']
                  if item['section'] == 'distribution' and item['field'] == 'quantity'}
        assert labels == {'vCore-hour', 'node-hour'}
        assert client.get(base + '/tables/unknown/rows').status_code == 404
        assert client.get(base + '/tables/azure_costs/rows?status=invalid').status_code == 422
        assert client.get(base + '/issues?version=old').status_code == 409
        assert client.get(base + '/reconciliation').status_code == 200
        assert client.get(base + '/records/unknown').status_code == 404


def test_corrupt_or_mismatched_artifacts_fail_closed(build_small, tmp_path):
    data, out, version, _ = build_small
    path = out / 'silver' / version / 'profiles.csv'
    contents = path.read_bytes()
    path.write_bytes(contents + b'\n')
    with TestClient(create_app(out, tmp_path / 'dist')) as client:
        assert client.get('/api/v1/silver').status_code == 503
    with pytest.raises(ValueError, match='hash mismatch'):
        publish(out)
    path.write_bytes(contents)
    (data / TEMPLATES[0]).write_bytes(b'new snapshot\n')
    snapshot(data, out)
    with TestClient(create_app(out, tmp_path / 'dist')) as client:
        assert client.get('/api/v1/silver').status_code == 503



def test_ownership_gaps_usage_roles_and_pool_evidence():
    from src.normalize import enrich, relationships
    from src.silver_profiles import gaps

    tables = {name: [] for name in SOURCE_TABLES}
    resources = [
        adapted('mapping_departments_tools', resource_id='ai-agent', department='IT'),
        adapted('mapping_departments_tools', 3, resource_id='vm-test', department='Sales'),
        adapted('mapping_departments_tools', 4, resource_id='gpu-ml', department='Consulting',
                default_project='P004'),
    ]
    asset = adapted('server_inventory', server_id='gpu-ml-01', type='ml', project_id='P-004')
    usage = adapted('ai_usage', department='Sales')
    week = adapted('server_metrics_weekly', server_id='gpu-ml-01', gpu_avg_pct='')
    unknown_week = adapted('server_metrics_weekly', 3, server_id='unknown', gpu_avg_pct='')
    tables.update(mapping_departments_tools=resources, server_inventory=[asset],
                  ai_usage=[usage], server_metrics_weekly=[week, unknown_week])
    mapped, inventory, centers = enrich(tables)
    assert len(centers['4500']) == 3
    assert usage.row['consumer_department'] == 'Sales' and usage.row['owner_department'] == 'IT'
    assert week.row['inventory_record_id'] == asset.id
    assert 'gpu_avg_pct' not in week.not_applicable | unknown_week.not_applicable
    assert any(issue['code'] == 'unknown_gpu_applicability' for issue in unknown_week.issues)
    charges = [adapted('azure_costs', ResourceId='path/gpu-ml'),
               adapted('aws_costs', line_item_resource_id='arn:aws:vm-test')]
    gpu, pool = relationships(mapped, inventory, charges)
    assert gpu['confidence'] == 'candidate' and gpu['server_id'] == 'gpu-ml-01'
    assert pool['confidence'] == 'unresolved' and pool['server_id'] is None
    assert 'allocation_weight' not in pool
    support = [adapted('aws_costs', pricing_unit='month', line_item_resource_id='arn:support',
                       line_item_usage_start_date=f'2026-0{month}-01 00:00:00')
               for month in (1, 3)]
    gap, = gaps('aws_costs', support, 'full')
    assert gap['count'] == 1 and '2026-02-01' in gap['description']
