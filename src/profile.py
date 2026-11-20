"""Deterministic, read-only EDA. Usage observations never become additional bills."""
import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from src.ingest import CORE_FILES, TEMPLATES, ROOT, snapshot
from src.source_specs import SPECS, canonical_mapping

START, END = date(2025, 9, 1), date(2026, 8, 31)
VERSION = '2.0'
DATE_FORMATS = {'date': '%Y-%m-%d', 'swiss_date': '%d.%m.%Y', 'timestamp': '%Y-%m-%d %H:%M:%S'}
OPTIONAL_TEXT = {'Notes', 'Remark', 'line_item_description', 'public_holiday', 'company_holidays'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def read_csv(path, expected=None):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, strict=True)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise ValueError(f'{path.name}: missing or duplicate header')
        if expected and columns != list(expected):
            raise ValueError(f'{path.name}: schema mismatch; expected {list(expected)}, received {columns}')
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f'{path.name}: inconsistent record width')
    return columns, rows


def parse(value, kind):
    if not value.strip(): return None
    if kind in DATE_FORMATS: return datetime.strptime(value, DATE_FORMATS[kind]).date()
    if kind in ('number', 'binary'):
        number = float(value)
        if not math.isfinite(number) or (kind == 'binary' and number not in (0, 1)): raise ValueError('invalid number')
        return number
    if kind == 'json':
        obj = json.loads(value)
        if not isinstance(obj, dict): raise ValueError('JSON must be an object')
        return obj
    return value


def period_sequence(start, end, cadence):
    current = start.replace(day=1) if cadence == 'monthly' else start
    while current <= end:
        yield current
        if cadence == 'monthly': current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        else: current += timedelta(days=7 if cadence == 'weekly' else 1)


def histogram(values):
    if not values: return []
    lo, hi = min(values), max(values)
    if lo == hi: return [{'label': f'{lo:g}', 'count': len(values)}]
    width = (hi-lo)/8
    counts = [0]*8
    for v in values: counts[min(7, int((v-lo)/width))] += 1
    return [{'label': f'{lo+i*width:.3g}–{lo+(i+1)*width:.3g}', 'count': n} for i,n in enumerate(counts)]


def resource_key(name, row):
    col = SPECS[name].resource
    value = row.get(col, '').strip()
    if name == 'azure_costs.csv': return value.rstrip('/').rsplit('/', 1)[-1]
    if name == 'aws_costs.csv': return value.rsplit(':', 1)[-1].rsplit('/', 1)[-1]
    return value


def applicable(name, col, row, inventory):
    if col == 'gpu_avg_pct': return inventory.get(row['server_id'], {}).get('type') == 'ml'
    if col == 'AvgCpuPercent': return row['UnitOfMeasure'] in ('vCore-hour', 'node-hour', 'vCPU-hour', 'GPU-hour')
    if col == 'avg_cpu_utilization': return row['pricing_unit'] == 'vCPU-hour'
    if col == 'object_requests': return row['pricing_unit'] == 'GB-day'
    if col == 'Accesses': return row['Service'] == 'Storage'
    return True


def make_view(name, records, inventory):
    spec = SPECS[name]
    issues = []
    def issue(code, cols, refs, message, severity='warning'):
        if refs:
            issues.append({'code': code, 'severity': severity, 'source': name, 'columns': cols, 'count': len(refs), 'rows': refs,
                           'message': message, 'examples': [{'source_row': n, 'values': {c:r[c] for c in (cols or spec.key.split())}} for n,r,_ in records if n in set(refs[:3])][:3]})
    fields = []
    for col, kind in spec.types.items():
        present = [(n,r[col],p[col]) for n,r,p in records if r[col].strip()]
        invalid = [n for n,_,v in present if v is None]
        blank = [n for n,r,_ in records if not r[col].strip()]
        expected_blank = [n for n,r,_ in records if not r[col].strip() and (col in OPTIONAL_TEXT or not applicable(name,col,r,inventory))]
        missing = sorted(set(blank)-set(expected_blank))
        valid = [v for _,_,v in present if v is not None]
        numeric = [v for v in valid if isinstance(v, (float,int))]
        dates = [v.isoformat() for v in valid if isinstance(v,date)]
        values = dates or numeric
        group_col = spec.currency if col == spec.amount and spec.currency in spec.types else next((u for u in ('UnitOfMeasure','pricing_unit','Unit') if u in spec.types), None) if col in ('Quantity','line_item_usage_amount') else None
        grouped_values = defaultdict(list)
        if group_col:
            for _,raw,typed in records:
                if typed[col] is not None: grouped_values[raw[group_col]].append(typed[col])
        distributions = [{'label':label,'count':len(vals),'minimum':min(vals),'maximum':max(vals),'mean':statistics.fmean(vals),'median':statistics.median(vals),'histogram':histogram(vals)} for label,vals in sorted(grouped_values.items())]
        mixed = len(distributions)>1
        observed = kind if valid and not invalid else 'mixed' if valid else 'unknown'
        fields.append({'name': col, 'expected_type': kind, 'observed_type': observed, 'blanks': len(blank), 'expected_blank': len(expected_blank),
                       'missing': len(missing), 'invalid': len(invalid), 'distinct': len({s for _,s,_ in present}),
                       'applicable_rows': sum(applicable(name,col,r,inventory) for _,r,_ in records),
                       'minimum': min(values) if values else None, 'maximum': max(values) if values else None,
                       'mean': statistics.fmean(numeric) if numeric and not mixed else None, 'median': statistics.median(numeric) if numeric and not mixed else None,
                       'histogram': histogram(numeric) if not mixed else [], 'distributions': distributions})
        issue('missing_value', [col], missing, 'Not recorded; never interpreted as zero.')
        issue('invalid_value', [col], invalid, f'Does not satisfy the documented {kind} type.')
        violations = []
        for n,r,p in records:
            value = p[col]
            if not isinstance(value,(float,int)): continue
            if ('pct' in col or 'Percent' in col or 'utilization' in col) and not 0 <= value <= 100: violations.append(n)
            elif col in ('runtime_h','active_use_h') and not 0 <= value <= 24: violations.append(n)
            elif col == 'uptime_h' and not 0 <= value <= 168: violations.append(n)
            elif col == 'runtime_h_30d' and not 0 <= value <= 720: violations.append(n)
            elif col in ('eur_chf','usd_chf') and value <= 0: violations.append(n)
            elif kind == 'number' and col != spec.amount and value < 0: violations.append(n)
        issue('numeric_constraint', [col], sorted(set(violations)), 'Value outside documented measurement bounds.')
    for left,right in [('licences_active_30d','licences_purchased'),('tokens_in_cache','tokens_in'),('active_use_h','runtime_h'),('cpu_avg_pct','cpu_max_pct')]:
        if left in spec.types and right in spec.types:
            issue('inconsistent_measurement',[left,right],[n for n,_,p in records if p[left] is not None and p[right] is not None and p[left]>p[right]],f'{left} exceeds {right}.')
    exact, keys = defaultdict(list), defaultdict(list)
    key_cols = spec.key.split()
    for n,r,_ in records:
        exact[tuple(r.values())].append(n)
        keys[tuple(r[c] for c in key_cols)].append(n)
    exact_groups = [refs for refs in exact.values() if len(refs)>1]
    key_groups = [refs for refs in keys.values() if len(refs)>1]
    for refs in exact_groups: issue('exact_duplicate_candidate', [], refs, 'Identical raw fields; retain pending semantic review.')
    for refs in key_groups: issue('business_key_collision', key_cols, refs, 'Repeated candidate grain; may be legitimate. Not a deletion instruction.')
    issue('missing_identifier',key_cols,[n for n,r,_ in records if any(not r[c].strip() for c in key_cols)],'Candidate key is incomplete.')
    conflicts = []
    if 'contract_status' in spec.types:
        versions = defaultdict(list)
        for n,r,_ in records: versions[tuple(r[c] for c in key_cols if c != 'contract_status')].append((n,r))
        for key, values in versions.items():
            if {'Draft','Final'} <= {r['contract_status'] for _,r in values}:
                refs=[n for n,_ in values]; conflicts.append({'key': list(key),'rows': refs})
                issue('draft_final_coexistence',key_cols,refs,'Both versions retained; Phase 3 baseline uses Final only.')
        issue('unknown_contract_status',['contract_status'],[n for n,r,_ in records if r['contract_status'] not in ('Draft','Final')],'Status is neither Draft nor Final.')
    categories = {c:dict(sorted(Counter(r[c] for _,r,_ in records).items())) for c in spec.types if c in ('currency','BillingCurrency','line_item_currency_code','contract_status','ChargeType','line_item_line_item_type','Unit','UnitOfMeasure','pricing_unit','billing')}
    projects = defaultdict(Counter)
    tag_info = {'empty_objects':0,'absent_keys':{},'blank_values':{},'invalid_rows':[]}
    tag_missing, tag_empty_values = defaultdict(list), defaultdict(list)
    for n,r,p in records:
        for c in spec.types:
            if 'project' in c.lower(): projects[c][r[c]] += 1
        if name == 'azure_costs.csv':
            tags=p['Tags']
            if tags is None: tag_info['invalid_rows'].append(n); continue
            if not tags: tag_info['empty_objects'] += 1
            for key in ('department','tool','project','environment'):
                if key not in tags: tag_missing[key].append(n)
                elif tags[key] is None or str(tags[key]).strip()=='': tag_empty_values[key].append(n)
            projects['Tags.project'][str(tags.get('project',''))] += 1
    for key,refs in tag_missing.items(): issue('missing_tag',['Tags'],refs,f'Azure JSON object has no {key} key.'); tag_info['absent_keys'][key]=len(refs)
    for key,refs in tag_empty_values.items(): issue('blank_tag',['Tags'],refs,f'Azure {key} tag is blank.'); tag_info['blank_values'][key]=len(refs)
    variants=[]
    for col, counts in projects.items():
        grouped=defaultdict(dict)
        for raw,count in sorted(counts.items()):
            match=re.fullmatch(r'[Pp]-?(\d{3})',raw.strip())
            proposed=f'P-{match[1]}' if match else None
            grouped[proposed or 'unknown'][raw]=count
        for proposed, values in sorted(grouped.items()): variants.append({'column':col,'proposed':proposed,'variants':values})
        refs=[n for n,r,p in records if (raw:=str((p.get('Tags') or {}).get('project','')) if col=='Tags.project' else r[col]) and re.fullmatch(r'[Pp]-?\d{3}',raw) and raw != 'P-'+raw[-3:]]
        issue('project_id_variant',['Tags'] if col=='Tags.project' else [col],refs,'Equivalent spelling candidate only; original ID retained.')
    amounts=[]
    if spec.amount:
        grouped=defaultdict(list)
        for n,r,p in records:
            currency=r.get(spec.currency,spec.currency)
            charge=r.get('ChargeType',r.get('line_item_line_item_type',r.get('contract_status','reported')))
            grouped[(currency,charge)].append((n,p[spec.amount]))
        for (currency,charge), values in sorted(grouped.items()):
            negative=[n for n,v in values if v is not None and v<0]
            amounts.append({'currency':currency,'charge_type':charge,'rows':len(values),'missing':sum(v is None for _,v in values),'negative_count':len(negative),'negative_rows':negative})
        if name=='azure_costs.csv': issue('credit_sign_mismatch',[spec.amount,'ChargeType'],[n for n,r,p in records if p[spec.amount] is not None and ((r['ChargeType']=='Credit' and p[spec.amount]>=0) or (r['ChargeType']!='Credit' and p[spec.amount]<0))],'Credit classification and amount sign disagree.')
    # Per-entity gaps are observations, not proof of downtime or an active lifetime.
    coverage=None; gaps=[]; boundary=[]; monthly=Counter()
    dated=[(n,r,p[spec.date]) for n,r,p in records if spec.date and p[spec.date] is not None]
    if dated:
        observed={d for _,_,d in dated}
        coverage={'minimum':min(observed).isoformat(),'maximum':max(observed).isoformat(),'distinct_periods':len(observed),'cadence':spec.cadence}
        for _,_,d in dated: monthly[d.strftime('%Y-%m')] += 1
        if spec.cadence in ('daily','weekly','monthly'):
            entities=defaultdict(set)
            for _,r,d in dated: entities[' | '.join(r[c] for c in spec.entity.split()) or 'source'].add(d)
            for entity, periods in sorted(entities.items()):
                missing=[d.isoformat() for d in period_sequence(min(periods),max(periods),spec.cadence) if d not in periods]
                # Baseline comparison is explicitly uncertain for entities without lifetimes.
                expected_start=START-timedelta(days=START.weekday()) if spec.cadence=='weekly' else START
                absent=[d.isoformat() for d in period_sequence(expected_start,END,spec.cadence) if d not in periods]
                if missing or absent: gaps.append({'entity':entity,'internal_gaps':missing,'baseline_absent_periods':absent,'certainty':'confirmed calendar/FX gap' if name in ('business_calendar.csv','exchange_rates.csv') else 'observation gap; lifetime/expected activity unverified'})
            if gaps: issues.append({'code':'coverage_gap','severity':'warning','source':name,'columns':[spec.date],'count':sum(len(set(g['internal_gaps']) | set(g['baseline_absent_periods'])) for g in gaps),'rows':[],'message':'Absent observations have no source row; see gap dates. Missing activity does not imply shutdown.','examples':[]})
        if spec.cadence=='weekly':
            boundary=[n for n,_,d in dated if d<=END and d+timedelta(days=6)>=START and (d<START or d+timedelta(days=6)>END)]
            issue('weekly_boundary_overlap',[spec.date],boundary,'Seven-day measurement overlaps the baseline boundary; no proration performed.')
    cells=len(records)*len(spec.types)
    return {'rows':len(records),'column_count':len(fields),'columns':fields,'issues':issues,'issue_counts':dict(sorted(Counter(i['code'] for i in issues).items())),
            'missing_cells':sum(f['missing'] for f in fields),'blank_cells':sum(f['blanks'] for f in fields),'cell_count':cells,
            'missing_percent':round(100*sum(f['missing'] for f in fields)/cells,4) if cells else None,
            'candidate_key':key_cols,'unique_key_count':len(keys),'key_collision_groups':key_groups,'exact_duplicate_groups':exact_groups,
            'duplicate_excess':sum(len(g)-1 for g in exact_groups),'contract_conflicts':conflicts,'categories':categories,'project_variants':variants,
            'azure_tags':tag_info if name=='azure_costs.csv' else None,'amounts':amounts,'date_coverage':coverage,'gaps':gaps,
            'boundary_rows':boundary,'monthly_rows':[{'month':m,'rows':n} for m,n in sorted(monthly.items())]}


def assess_joins(name, records, tables):
    spec=SPECS[name]; joins=[]
    def assess(label,target,left,right,notes, columns):
        index=defaultdict(list)
        for _,r,_ in tables[target]:
            key=right(r)
            if key: index[key].append(r)
        blank=[]; unmatched=[]; ambiguous=[]; matched=[]; conflicts=[]; missing_department=[]
        for n,r,p in records:
            key=left(r)
            if not key: blank.append(n); continue
            hits=index.get(key,[])
            if not hits: unmatched.append(n)
            elif len(hits)>1: ambiguous.append(n)
            else:
                matched.append(n)
                direct=(p.get('Tags') or {}).get('department') if name=='azure_costs.csv' else r.get('resource_tags_user_department',r.get('department',''))
                target_dept=hits[0].get('department','')
                if target=='mapping_departments_tools.csv' and not target_dept: missing_department.append(n)
                if target_dept and direct and direct!=target_dept: conflicts.append(n)
        joins.append({'label':label,'target':target,'columns':columns,'cardinality':'many-to-one' if not any(len(v)>1 for v in index.values()) else 'potential many-to-many',
                      'matched':len(matched),'unmatched':len(unmatched),'blank_keys':len(blank),'ambiguous':len(ambiguous),'unmatched_rows':unmatched,'blank_rows':blank,'ambiguous_rows':ambiguous,'ownership_conflict_rows':conflicts,'missing_department_rows':missing_department,'notes':notes})
    if spec.resource and name!='mapping_departments_tools.csv':
        target='server_inventory.csv' if name=='server_metrics_weekly.csv' else 'mapping_departments_tools.csv'
        right_col='server_id' if target=='server_inventory.csv' else 'resource_id'
        assess('Resource / asset mapping',target,lambda r:resource_key(name,r),lambda r:r[right_col],'Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.',[spec.resource])
    if name=='hoster_invoice.csv': assess('Hoster label to tool','mapping_departments_tools.csv',lambda r:r['Item'],lambda r:r['tool'],'Use only unique label matches; Item is not a resource identifier.',['Item'])
    if spec.center:
        # Distinct department associations, not raw master rows: avoids false ambiguity from multiple resources.
        target='mapping_departments_tools.csv'
        original=tables[target]
        associations=sorted({(r['cost_center'],r['department']) for _,r,_ in original if r['department']})
        tables[target]=[(0,{'cost_center':c,'department':d}, {}) for c,d in associations]
        assess('Cost center to department',target,lambda r:r[spec.center],lambda r:r['cost_center'],'Distinct department associations only. Blank departments stay unknown, never default to IT.',[spec.center])
        tables[target]=original
    if spec.amount and spec.currency not in ('CHF',''):
        assess('Transaction month to FX','exchange_rates.csv',lambda r:r[spec.date][:7],lambda r:r['month'][:7],'Monthly EUR/USD CHF-per-unit rates; no conversion performed.',[spec.date,spec.currency])
    return joins


def profile(data):
    tables={}; inputs=[]
    for name in (*CORE_FILES,*TEMPLATES): inputs.append({'name':name,'sha256':hashlib.sha256((data/name).read_bytes()).hexdigest()})
    snapshot_id=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    for name in CORE_FILES:
        spec=SPECS[name]; _,rows=read_csv(data/name,spec.types)
        parsed=[]
        for n,row in enumerate(rows,2):
            typed={}
            for c,kind in spec.types.items():
                try: typed[c]=parse(row[c],kind)
                except (ValueError,TypeError,OverflowError): typed[c]=None
            parsed.append((n,row,typed))
        tables[name]=parsed
    inventory={r['server_id']:r for _,r,_ in tables['server_inventory.csv']}
    sources=[]
    for name in CORE_FILES:
        spec=SPECS[name]; records=tables[name]
        baseline=[rec for rec in records if spec.date and (d:=rec[2][spec.date]) is not None and d<=END and (d+timedelta(days=6) if spec.cadence=='weekly' else d)>=START] if spec.date else records
        views={}
        for scope, subset in [('full',records),('baseline',baseline)]:
            view=make_view(name,subset,inventory)
            view['scope_note']='Snapshot/master context, not historical baseline measurements.' if not spec.date else 'Weekly intervals overlapping the period; no proration.' if spec.cadence=='weekly' else 'All records in the export.' if scope=='full' else 'Records dated within the baseline; drafts and duplicate candidates retained.'
            view['joins']=assess_joins(name,subset,tables)
            for join in view['joins']:
                for code,key,message in [('unmatched_join','unmatched_rows','No matching target key.'),('missing_join_key','blank_rows','Join key is blank.'),('ambiguous_join','ambiguous_rows','Multiple target matches would multiply rows.'),('ownership_conflict','ownership_conflict_rows','Source ownership contradicts the resource master.'),('missing_department_mapping','missing_department_rows','Matching resource master has no department.')]:
                    refs=join[key]
                    if refs: view['issues'].append({'code':code,'severity':'warning','source':name,'columns':join['columns'],'count':len(refs),'rows':refs,'message':f"{join['label']}: {message}",'examples':[]})
            view['issue_counts']=dict(sorted(Counter(i['code'] for i in view['issues']).items()))
            views[scope]=view
        sources.append({'name':name,'role':spec.role,'cadence':spec.cadence,'sha256':next(i['sha256'] for i in inputs if i['name']==name),'canonical_mapping':canonical_mapping(name),'views':views})
    templates=[]
    for name in TEMPLATES:
        cols,rows=read_csv(data/name)
        templates.append({'name':name,'columns':cols,'rows':len(rows),'parameters':[{'parameter':r['parameter'],'unit':r['unit'],'status':'unknown; factors/estimates or Phase 3+ calculation required'} for r in rows] if 'parameter' in cols else [],'status':'Read-only official template; example measure rows are not proposed savings.'})
    report={'schema_version':2,'profiling_version':VERSION,'snapshot_id':snapshot_id,'inputs':inputs,'baseline':{'start':START.isoformat(),'end':END.isoformat()},'sources':sources,'templates':templates,
            'limitations':['No records removed, normalized, allocated or financially reconciled.','Pool membership gpu-ml → gpu-ml-01 and vm-test → test/QA/UAT/DR instances needs Phase 3 evidence; no pooled invoice is multiplied across instances.','AI gateway reported costs are not additional provider invoices. No energy, carbon or savings factors are supplied.','Free text is untrusted evidence, never instructions. Safety decisions require the later safety phase.','Issue counts count findings/groups, not disjoint bad rows. A row may have several issues.','Source rows are logical CSV record numbers including header, not physical text line numbers.']}
    report['report_id']=digest(report)
    return report


def render_map(report):
    lines=['# Data map and exploratory analysis','',f"Snapshot: `{report['snapshot_id']}` · Report: `{report['report_id']}`",'',f'Baseline: {START} through {END} inclusive. All 13 core sources parsed successfully.','',*['- '+s for s in report['limitations']],'','## Source catalog','','| Source | Role | Rows (full / baseline) | Columns | Exact duplicate excess |','|---|---|---:|---:|---:|']
    for s in report['sources']:
        f,b=s['views']['full'],s['views']['baseline'];lines.append(f"| {s['name']} | {s['role']} | {f['rows']} / {b['rows']} | {f['column_count']} | {f['duplicate_excess']} |")
    for s in report['sources']:
        lines += ['',f"## {s['name']}",'',f"Role: {s['role']}. Candidate key: {', '.join(s['views']['full']['candidate_key'])}. SHA-256: `{s['sha256']}`."]
        for scope,v in s['views'].items():
            lines += ['',f'### {scope.title()} export profile','',v['scope_note'],'',f"Rows: {v['rows']}; missing cells: {v['missing_cells']}; expected optional/non-applicable blanks: {v['blank_cells']-v['missing_cells']}; exact duplicate excess: {v['duplicate_excess']}; key collision groups: {len(v['key_collision_groups'])}.",'','| Field | Expected / observed type | Missing / blank / invalid | Min | Max |','|---|---|---:|---|---|']
            for f in v['columns']: lines.append(f"| {f['name']} | {f['expected_type']} / {f['observed_type']} | {f['missing']} / {f['blanks']} / {f['invalid']} | {f['minimum']} | {f['maximum']} |")
            lines += ['', 'Categories: `'+json.dumps(v['categories'],sort_keys=True)+'`','', 'Amount/credit counts (not cost totals): `'+json.dumps(v['amounts'])+'`','', 'Project spelling candidates: `'+json.dumps(v['project_variants'])+'`']
            if v['azure_tags']: lines += ['', 'Azure JSON diagnostics: `'+json.dumps(v['azure_tags'])+'`']
            lines += ['','Coverage: `'+json.dumps(v['date_coverage'])+'`']
            for gap in v['gaps']: lines += [f"- {gap['entity']}: {gap['certainty']}; internal gaps: {', '.join(gap['internal_gaps']) or 'none'}; baseline absent periods: {', '.join(gap['baseline_absent_periods']) or 'none'}."]
            lines += ['','#### Proposed joins','']
            for j in v['joins']: lines += [f"- {j['label']} → {j['target']}: {j['cardinality']}; matched {j['matched']}, unmatched {j['unmatched']}, blank {j['blank_keys']}, ambiguous {j['ambiguous']}, ownership conflicts {len(j['ownership_conflict_rows'])}. {j['notes']}"]
            lines += ['','Issue categories: `'+json.dumps(v['issue_counts'])+'`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.']
        lines += ['','### Canonical field mapping (proposed, not executed)','','| Canonical field | Source | Rule / fallback |','|---|---|---|']
        for field,m in s['canonical_mapping'].items(): lines.append(f"| {field} | {m['source']} | {m['rule']} |")
    lines += ['','## Official templates','']
    for t in report['templates']: lines += [f"### {t['name']}",'',t['status'],'','Headers (exact order): `'+', '.join(t['columns'])+'`','',*['- '+p['parameter']+' ('+p['unit']+'): '+p['status'] for p in t['parameters']],'']
    lines += ['## Source relationships and next phases','','Monitoring, assets and operational evidence are distinct from financial facts. Contract metadata (end, notice, billing) is not an event date. Inventory was exported as of 2026-09-06; 30-day values must not stand in for the entire baseline.','', 'Energy/emissions factors, shared allocation, signed monthly FX conversion, Final-only financial selection, semantic deduplication and pooled asset relationships belong to Phase 3 and later. Unknown numeric fields remain null; ownership remains unknown until verified (Phase 3 display: Unallocated).']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'data');parser.add_argument('--out',type=Path,default=ROOT/'outputs');parser.add_argument('--docs',type=Path,default=ROOT/'docs')
    args=parser.parse_args()
    try:
        report=profile(args.data)
        manifest=snapshot(args.data,args.out)
        if manifest['snapshot_id']!=report['snapshot_id']: raise ValueError('Sources changed while profiling; rerun.')
        args.docs.mkdir(parents=True,exist_ok=True)
        temp=args.out/'data_quality.tmp'
        temp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8');temp.replace(args.out/'data_quality.json')
        (args.docs/'DATA_MAP.md').write_text(render_map(report),encoding='utf-8')
    except (OSError,ValueError,csv.Error) as error: parser.exit(1,f'Profiling failed: {error}\n')
    print(json.dumps({'report_id':report['report_id'],'sources':len(report['sources']),'raw_rows':sum(s['views']['full']['rows'] for s in report['sources'])}))
if __name__=='__main__': main()
