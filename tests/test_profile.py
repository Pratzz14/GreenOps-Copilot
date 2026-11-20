"""Profiling contract, evidence preservation, and API regression coverage."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.quality import load_quality
from backend.quality_models import Report
from src.ingest import CORE_FILES, TEMPLATES, ROOT, snapshot
from src.profile import profile, read_csv, parse, make_view, assess_joins, digest, render_map
from src.source_specs import SPECS, CANONICAL_FIELDS


def records(name, overrides):
    fields, source = read_csv(ROOT/'data'/'bronze'/name)
    result=[]
    for n, changes in enumerate(overrides,2):
        raw={**source[0],**changes}
        typed={}
        for c,k in SPECS[name].types.items():
            try: typed[c]=parse(raw[c],k)
            except (ValueError,TypeError): typed[c]=None
        result.append((n,raw,typed))
    return result


@pytest.fixture(scope='module')
def real_report():
    before={n:hashlib.sha256((ROOT/'data'/'bronze'/n).read_bytes()).hexdigest() for n in (*CORE_FILES,*TEMPLATES)}
    value=profile(ROOT/'data')
    assert before=={n:hashlib.sha256((ROOT/'data'/'bronze'/n).read_bytes()).hexdigest() for n in before}
    return value


def test_real_sources_counts_mapping_gaps_and_reproducibility(real_report):
    Report.model_validate(real_report)
    assert real_report==profile(ROOT/'data')
    by_name={s['name']:s for s in real_report['sources']}
    assert len(by_name)==13
    assert sum(s['views']['full']['rows'] for s in by_name.values())==70583
    for name,n in [('server_inventory.csv',53),('mapping_departments_tools.csv',90),('ai_subscriptions.csv',261)]:
        assert by_name[name]['views']['full']['rows']==n
    for s in by_name.values(): assert set(s['canonical_mapping'])==set(CANONICAL_FIELDS)
    metrics=by_name['server_metrics_weekly.csv']['views']['baseline']
    gpu=next(c for c in metrics['columns'] if c['name']=='gpu_avg_pct')
    assert gpu['missing']==0 and gpu['expected_blank']>2000
    assert metrics['boundary_rows']
    platform=by_name['data_platform_usage.csv']['views']['baseline']
    dev=next(g for g in platform['gaps'] if g['entity']=='dp-dev')
    assert dev['baseline_absent_periods']==['2025-10-24','2025-11-12','2025-12-01','2026-02-12','2026-04-30','2026-06-23']
    assert platform['duplicate_excess']==2
    assert by_name['business_calendar.csv']['views']['baseline']['rows']==365
    assert by_name['exchange_rates.csv']['views']['baseline']['rows']==12
    azure=by_name['azure_costs.csv']['views']['full']
    assert sum(a['negative_count'] for a in azure['amounts'])==3
    quantity=next(c for c in azure['columns'] if c['name']=='Quantity')
    assert len(quantity['distributions'])==6
    assert quantity['mean'] is None and quantity['histogram']==[]
    assert sum(d['count'] for d in quantity['distributions'])==azure['rows']
    text=render_map(real_report)
    assert all(n in text for n in CORE_FILES)
    assert 'cost_chf' in text and 'unknown' in text


def test_csv_bom_quoted_comma_and_embedded_newline(tmp_path):
    p=tmp_path/'source.csv'
    p.write_text('id,note\r\n001,"quoted, text\nsecond line"\r\n',encoding='utf-8-sig',newline='')
    cols,rows=read_csv(p,['id','note'])
    assert cols==['id','note'] and rows==[{'id':'001','note':'quoted, text\nsecond line'}]


@pytest.mark.parametrize('content',['a,a\n1,2\n','a,b\n1\n','a,b\n1,2,3\n','a,b\n1,"unfinished','x,y\n1,2'])
def test_schema_and_structural_failures(tmp_path,content):
    p=tmp_path/'bad.csv';p.write_text(content)
    with pytest.raises((ValueError,csv.Error)):read_csv(p,['a','b'])


@pytest.mark.parametrize('value,kind',[('NaN','number'),('inf','number'),('2','binary'),('2026-02-30','date'),('2026/01/01','date'),('[]','json'),('{bad','json')])
def test_invalid_typed_values(value,kind):
    with pytest.raises(ValueError):parse(value,kind)


def test_types_dates_and_empty_values():
    assert str(parse('01.11.2024','swiss_date'))=='2024-11-01'
    assert str(parse('2026-08-31 00:00:00','timestamp'))=='2026-08-31'
    assert parse('','number') is None
    assert parse('4500','text')=='4500'


def test_duplicates_versions_constraints_and_raw_projects():
    rs=records('ai_subscriptions.csv',[{'month':'2026-08-01','contract_status':'Final'},{'month':'2026-08-01','contract_status':'Final'},{'month':'2026-08-01','contract_status':'Draft','licences_active_30d':'9999'}])
    view=make_view('ai_subscriptions.csv',rs,{})
    assert view['exact_duplicate_groups']==[[2,3]]
    assert view['key_collision_groups']==[[2,3]]
    assert len(view['contract_conflicts'])==1
    assert any(i['code']=='inconsistent_measurement' for i in view['issues'])
    ai=records('ai_usage.csv',[{'project_id':'P001'},{'project_id':'p-001'},{'project_id':'P-001','tokens_in_cache':'9999999999'}])
    v=make_view('ai_usage.csv',ai,{})
    assert v['project_variants']==[{'column':'project_id','proposed':'P-001','variants':{'P-001':1,'P001':1,'p-001':1}}]
    assert ai[0][1]['project_id']=='P001'
    assert any(i['code']=='inconsistent_measurement' for i in v['issues'])


def test_azure_tags_invalids_and_signed_credits():
    rs=records('azure_costs.csv',[{'Tags':'{}','ChargeType':'Credit','CostInBillingCurrency':'-12'},{'Tags':'{"department":""}','ChargeType':'Credit','CostInBillingCurrency':'12'},{'Tags':'[]','Date':'invalid','Quantity':'NaN'}])
    view=make_view('azure_costs.csv',rs,{})
    assert view['azure_tags']['empty_objects']==1
    assert view['azure_tags']['invalid_rows']==[4]
    assert view['azure_tags']['blank_values']['department']==1
    assert any(i['code']=='credit_sign_mismatch' and i['rows']==[3] for i in view['issues'])
    assert sum(a['negative_count'] for a in view['amounts'])==1
    assert next(c for c in view['columns'] if c['name']=='Date')['invalid']==1


def test_weekly_boundary_and_unknown_lifetimes():
    rs=records('server_metrics_weekly.csv',[{'week_start':'2026-08-24'},{'week_start':'2026-08-31'}])
    v=make_view('server_metrics_weekly.csv',rs,{})
    assert v['boundary_rows']==[3]
    assert all('unverified' in g['certainty'] for g in v['gaps'])


def test_join_ambiguity_unmatched_fx_and_missing_departments():
    name='hoster_invoice.csv'
    rows=records(name,[{'Item':'duplicate','CostCenter':'9100'},{'Item':'absent','CostCenter':''}])
    master=records('mapping_departments_tools.csv',[{'tool':'duplicate','resource_id':'a','cost_center':'9100','department':''},{'tool':'duplicate','resource_id':'b','cost_center':'9100','department':''}])
    joins=assess_joins(name,rows,{'mapping_departments_tools.csv':master})
    assert joins[0]['ambiguous_rows']==[2] and joins[0]['unmatched_rows']==[3]
    aws=records('aws_costs.csv',[{'line_item_usage_start_date':'2026-08-31 00:00:00'}])
    tables={'mapping_departments_tools.csv':master,'exchange_rates.csv':records('exchange_rates.csv',[{'month':'2026-07-01'}])}
    j=assess_joins('aws_costs.csv',aws,tables)
    assert next(x for x in j if x['target']=='exchange_rates.csv')['unmatched']==1


@pytest.fixture()
def saved_report(tmp_path,real_report):
    data=tmp_path/'data'; data.mkdir()
    for name in (*CORE_FILES,*TEMPLATES): (data/name).write_bytes((ROOT/'data'/'bronze'/name).read_bytes())
    out=tmp_path/'outputs';snapshot(data,out)
    (out/'data_quality.json').write_text(json.dumps(real_report),encoding='utf-8')
    return out


def test_api_summary_detail_pagination_and_fail_closed(saved_report,monkeypatch):
    with TestClient(create_app(saved_report,saved_report/'no-dist')) as client:
        def forbidden(*args,**kwargs):raise AssertionError('GET touched disk')
        monkeypatch.setattr(Path,'read_text',forbidden);monkeypatch.setattr(Path,'read_bytes',forbidden)
        for scope in ('full','baseline'):
            overview=client.get('/api/v1/data-quality',params={'scope':scope})
            assert overview.status_code==200
            summary=overview.json()['sources'][0]
            assert 'views' not in summary
            detail=client.get('/api/v1/data-quality/sources/azure_costs.csv',params={'scope':scope}).json()
            assert summary['rows']==detail['profile']['rows']
            assert detail['profile']['issues']==[]
            page=client.get('/api/v1/data-quality/sources/azure_costs.csv/issues',params={'scope':scope,'limit':1,'offset':1,'code':'missing_value'}).json()
            assert len(page['items'])==1 and page['items'][0]['code']=='missing_value'
        assert client.get('/api/v1/data-quality/sources/unknown').status_code==404
        assert client.get('/api/v1/data-quality',params={'scope':'invalid'}).status_code==422
        assert client.get('/api/v1/data-quality/sources/azure_costs.csv/issues?limit=0').status_code==422
        assert client.get('/api/v1/data-quality/sources/azure_costs.csv/issues?offset=-1').status_code==422
        assert client.get('/api/v1/health').json()['data_ready'] is False
        assert client.get('/api/v1/runs/current').status_code==503


def test_report_missing_corrupt_mismatched_and_checksum(saved_report,real_report):
    p=saved_report/'data_quality.json'
    valid=json.loads(p.read_text())
    for value in [None,{},dict(valid,report_id='0'*64),dict(valid,snapshot_id='0'*64)]:
        p.write_text(json.dumps(value))
        report,error=load_quality(saved_report,real_report['snapshot_id'])
        assert report is None and error
    # A correctly checksummed but incomplete report still fails schema validation.
    value=dict(valid);value['sources']=value['sources'][:-1];value.pop('report_id');value['report_id']=digest(value)
    p.write_text(json.dumps(value));assert load_quality(saved_report,real_report['snapshot_id'])[0] is None
    p.unlink()
    with TestClient(create_app(saved_report,saved_report/'no-dist')) as client:
        assert client.get('/api/v1/data-quality').status_code==503
