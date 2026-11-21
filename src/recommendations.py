"""Recurring utilization findings and evidence-backed recommendations."""

from collections import defaultdict
from datetime import UTC, date, timedelta
from decimal import Decimal

from src.gold_baseline import key_for, region
from src.gold_measures import conflicts, local_at, one_year_after
from src.profile import read_csv
from src.platforms import service_platform
from src.silver_storage import silver_directory


SERVER_FIELDS = ('cpu_avg_pct', 'cpu_max_pct', 'ram_avg_pct', 'uptime_h')
TEMPLATES = {
    'Data cluster': ('schedule', 'Review scheduled pauses or downsizing.', 'Verify hourly jobs, protected periods and restart behavior.', 'Data platform owner'),
    'Server': ('shutdown', 'Review downsizing or a reversible pause.', 'Verify peak demand, dependencies, standby obligations and rollback.', 'Infrastructure owner'),
    'Licence': ('resize', 'Review reducing persistently unused seats at renewal.', 'Verify seat needs, minimum commitments, pricing and notice terms.', 'Procurement and product owner'),
}


def subject_id(provider, name, family):
    return f'{family}:{key_for(provider, name, family)}'


def unique_periods(rows, field):
    groups = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    return {period: group[0] for period, group in groups.items() if len(group) == 1}


def cluster_weeks(rows, weeks):
    grouped = defaultdict(list)
    for day, row in unique_periods(rows, 'event_date').items():
        if not day or not row['runtime_h'] or not row['active_use_h']:
            continue
        day = date.fromisoformat(day)
        week = (day - timedelta(days=day.weekday())).isoformat()
        runtime, active = Decimal(row['runtime_h']), Decimal(row['active_use_h'])
        if week in weeks and 0 <= active <= runtime:
            grouped[week].append((row, runtime, active))
    observed, qualifying = {}, {}
    for week, values in grouped.items():
        runtime = sum(value[1] for value in values)
        if len(values) >= 5 and runtime > 0:
            observed[week] = [value[0] for value in values]
            if sum(value[2] for value in values) * 5 <= runtime:
                qualifying[week] = observed[week]
    return observed, qualifying


def server_weeks(rows, weeks):
    observed, qualifying = {}, {}
    for week, row in unique_periods(rows, 'event_date').items():
        if week in weeks and all(row[field] for field in SERVER_FIELDS):
            observed[week] = [row]
            cpu, peak, ram, uptime = (Decimal(row[field]) for field in SERVER_FIELDS)
            if cpu <= 5 and peak <= 20 and ram <= 40 and uptime >= 120:
                qualifying[week] = [row]
    return observed, qualifying


def recurring(observed, qualifying, weeks, coverage):
    return (len(qualifying) >= 3 and len(qualifying) * 2 >= len(observed)
            and len(observed) * 100 >= len(weeks) * coverage
            and bool(qualifying.keys() & set(sorted(weeks)[-4:])))


def seat_gap(row):
    if not row or not row['licences_purchased'] or not row['licences_active_30d']:
        return 0
    purchased, active = int(row['licences_purchased']), int(row['licences_active_30d'])
    return purchased - active if 0 <= active <= purchased else 0


def findings(load, start, stop):
    days = [start + timedelta(days=index) for index in range((stop - start).days)]
    weeks = {day.isoformat() for day in days if day.weekday() == 0 and day + timedelta(days=7) <= stop}
    complete_months = [day.isoformat()[:7] for day in days if day.day == 1
                       and (day + timedelta(days=32)).replace(day=1) <= stop][-3:]
    mappings = {row['resource_id']: row for row in load('mapping_departments_tools')}
    relationships = defaultdict(set)
    for row in load('resource_relationships'):
        if row['confidence'] == 'high':
            relationships[row['server_id']].add(row['resource_id'])

    def infrastructure(kind, provider, name, family, observed, qualifying, source, billed=None):
        mapping = mappings.get(billed or name, {})
        months = (sorted({row['event_date'][:7] for rows in qualifying.values() for row in rows})
                  if kind == 'Data cluster' else
                  sorted({(date.fromisoformat(week) + timedelta(days=index)).isoformat()[:7]
                          for week in qualifying for index in range(7)}))
        return dict(category=kind, provider=provider, resource=name, label=name,
                    subject=subject_id(provider, name, family), billed_subject=subject_id(provider, billed, 'resource') if billed else None,
                    attribution=dict(provider=provider, tool=mapping.get('tool') or name,
                                     platform=service_platform('data_cluster' if kind == 'Data cluster' else 'server'),
                                     department=source.get('reporting_department') or mapping.get('department') or 'Unallocated',
                                     location=region(source.get('region'))),
                    observed=observed, qualifying=qualifying, months=months, persistent_unused=None)

    clusters = defaultdict(list)
    for row in load('data_platform_usage'):
        clusters[row.get('provider') or 'Azure', row['resource_id']].append(row)
    for (provider, name), rows in sorted(clusters.items()):
        observed, qualifying = cluster_weeks(rows, weeks)
        if recurring(observed, qualifying, weeks, 70):
            yield infrastructure('Data cluster', provider, name, 'resource', observed, qualifying, rows[0])

    telemetry = defaultdict(list)
    for row in load('server_metrics_weekly'):
        telemetry[row['server_id']].append(row)
    assets = defaultdict(list)
    for asset in load('assets'):
        assets[asset['server_id']].append(asset)
    for name, records in sorted(assets.items()):
        if len(records) != 1:
            continue
        asset = records[0]
        observed, qualifying = server_weeks(telemetry[name], weeks)
        if recurring(observed, qualifying, weeks, 75):
            links = relationships[name]
            yield infrastructure('Server', asset['provider'], name, 'server', observed, qualifying, asset,
                                 next(iter(links)) if len(links) == 1 else None)

    contracts = defaultdict(list)
    for row in load('contracts'):
        if row['contract_status'] == 'Final' and row['reporting_month'] in complete_months:
            contracts[row['provider'], row['product'] or row['contract'], row['cost_center'], row['source_file']].append(row)
    for (provider, name, center, file), rows in sorted(contracts.items()):
        history = unique_periods(rows, 'reporting_month')
        if len(complete_months) < 3 or not all(seat_gap(history.get(month)) > 0 for month in complete_months):
            continue
        family = 'ai_subscription' if file == 'ai_subscriptions.csv' else 'saas'
        departments = {row.get('reporting_department') or 'Unallocated' for row in history.values()}
        periods = {month: [history[month]] for month in complete_months}
        yield dict(category='Licence', provider=provider, resource=name, label=f'{name} · {center}' if center else name,
                   subject=subject_id(provider, name, family), billed_subject=None, center=center, file=file,
                   attribution=dict(provider=provider, department=next(iter(departments)) if len(departments) == 1 else 'Unallocated',
                                    tool=name, location='Mixed', platform=service_platform(family)),
                   observed=periods, qualifying=periods,
                   months=complete_months, persistent_unused=min(seat_gap(row) for row in history.values()))


def catalog(gold, output):
    directory = silver_directory(output) / gold.run['silver_version']

    def load(name):
        rows = read_csv(directory / f'{name}.csv')[1]
        return [row for row in rows if name == 'resource_relationships' or row['record_status'] == 'accepted']

    measures = {row['measure_id']: row for row in gold.measures()}
    by_subject, protections = defaultdict(list), defaultdict(list)
    for row in gold.select('''
        SELECT m.measure_id, m.subject_id, f.category, f.evidence_set_id
        FROM gold.measure m JOIN gold.finding f USING (run_id, finding_id) WHERE m.run_id=?
    '''):
        by_subject[row['subject_id']].append(row)
    for rule in gold.select("""
        SELECT * EXCLUDE (starts_at, ends_at), starts_at AT TIME ZONE 'UTC' AS starts_at,
               ends_at AT TIME ZONE 'UTC' AS ends_at
        FROM gold.protection_window WHERE run_id=? ORDER BY protection_id
    """):
        for field in ('starts_at', 'ends_at'):
            if rule[field] is not None:
                rule[field] = rule[field].replace(tzinfo=UTC)
        protections[rule['subject_id']].append(rule)
    contract_refs = defaultdict(set)
    for row in gold.select('''
        SELECT e.evidence_set_id, e.source_record_id FROM gold.evidence e
        JOIN gold.finding f USING (run_id, evidence_set_id)
        WHERE e.run_id=? AND source_file IN ('ai_subscriptions.csv', 'saas_contracts.csv')
    '''):
        contract_refs[row['evidence_set_id']].add(row['source_record_id'])
    contract_scopes = {row['record_id']: (row['source_file'], row['cost_center']) for row in load('contracts')}
    begin = local_at(gold.run['decision_as_of'])
    end = local_at(one_year_after(gold.run['decision_as_of']))

    for item in findings(load, gold.run['baseline_start'], gold.run['baseline_end_exclusive']):
        kind, subject = item['category'], item['subject']
        action, change, next_check, role = TEMPLATES[kind]
        category = {'Data cluster': 'platform_utilisation', 'Server': 'server_utilisation', 'Licence': 'licence_utilisation'}[kind]
        candidates = [row for row in by_subject[subject] if row['category'] == category]
        if kind == 'Licence':
            candidates = [row for row in candidates if {
                contract_scopes.get(ref) for ref in contract_refs[row['evidence_set_id']]
            } == {(item['file'], item['center'])}]
        measure = measures[candidates[0]['measure_id']] if len(candidates) == 1 else None
        related = protections[subject] + protections[item['billed_subject']]
        actions = {action, 'shutdown'} if action == 'schedule' else {action}
        applicable = [rule for rule in related if any(conflicts(rule, candidate, begin, end) for candidate in actions)]
        standing_block = any(rule['decision'] == 'blocked' and rule['starts_at'] is None and rule['ends_at'] is None
                             for rule in applicable)
        status = 'blocked' if standing_block else measure['safety_status'] if measure else 'human_review'
        if status == 'eligible' and applicable:
            status = 'human_review'
        if measure:
            change = measure['proposed_change']
            next_check = measure['risks_and_exceptions']
            role = measure['responsible_role'] or role
        if status == 'blocked' and applicable:
            next_check = ' '.join(dict.fromkeys(rule['reason'] for rule in applicable if rule['decision'] == 'blocked')) or next_check
            role = next((rule['responsible_role'] for rule in applicable if rule['decision'] == 'blocked'), role) or role
        identifier = key_for(subject, item.get('file'), item.get('center'), action)
        refs = [{'file': row['source_file'], 'row': int(row['source_row'])}
                for period in sorted(item['qualifying']) for row in item['qualifying'][period]]
        yield dict(id=identifier, finding_key=f"{kind}:{item['provider']}:{item['label']}",
                   category=kind, resource=item['label'], proposed_change=change, observed=len(item['observed']),
                   qualifying=len(item['qualifying']), months=item['months'], evidence=refs,
                   persistent_unused=item['persistent_unused'], cost_center=item.get('center') or None,
                   rule_status=status, responsible_role=role,
                   next_check=next_check, estimate=measure, attribution=item['attribution'],
                   decision_as_of=gold.run['decision_as_of'], action=action,
                   seat_history={month: rows[0] for month, rows in item['qualifying'].items()} if kind == 'Licence' else {},
                   billing_subject=subject if kind == 'Data cluster' else item['billed_subject'],
                   protection_evidence_ids=list(dict.fromkeys(rule['evidence_set_id'] for rule in applicable)))
