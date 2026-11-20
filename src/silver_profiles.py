"""Precompute Silver completeness, compatible distributions and observation gaps."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from statistics import mean, median

from src.profile import END, START, period_sequence
from src.silver_rules import OPTIONAL, slug
from src.source_specs import SPECS

PROFILE_FIELDS = ('table', 'scope', 'section', 'field', 'label', 'expected_type', 'observed_type',
                  'valid', 'missing', 'not_applicable', 'optional_blank', 'invalid',
                  'bronze_rows', 'bronze_missing', 'matched_bronze_missing', 'silver_rows',
                  'minimum', 'median', 'mean', 'maximum', 'bin', 'count', 'description')
DECIMALS = {'node_hours', 'uncached_input_tokens', 'amount_original', 'fx_rate', 'converted_cost_chf'}
INTEGERS = {'source_row', 'weekday_iso', 'utilization_window_days'}
BOOLEANS = {'baseline_overlap', 'baseline_context', 'baseline_boundary_week', 'baseline_eligible'}


@lru_cache(maxsize=None)
def schema(table):
    if table == 'assets':
        table = 'server_inventory'
    origins = ('ai_subscriptions', 'saas_contracts') if table == 'contracts' else (table,)
    if table == 'usage_facts':
        origins = ('ai_usage', 'data_platform_usage', 'server_metrics_weekly')
    return {slug(field): kind for origin in origins if f'{origin}.csv' in SPECS
            for field, kind in SPECS[f'{origin}.csv'].types.items()}


@lru_cache(maxsize=None)
def field_type(table, field):
    if field in BOOLEANS:
        return 'boolean'
    if field in INTEGERS:
        return 'integer'
    if (field in DECIMALS or (table == 'cost_facts' and field == 'cost_chf')
            or schema(table).get(field) in {'number', 'binary'}):
        return 'decimal'
    if field in {'event_date', 'week_end', 'snapshot_date'} or schema(table).get(field) in {'date', 'swiss_date'}:
        return 'date'
    return schema(table).get(field, 'text')


def measurement_label(row, table, field):
    if field in {'amount_original', slug(SPECS[f'{table}.csv'].amount)}:
        return row.get('original_currency') or 'Unknown currency'
    if field in {'converted_cost_chf', 'cost_chf'}:
        return 'Converted CHF' if field == 'converted_cost_chf' else 'Reported CHF'
    if field == 'fx_rate':
        return f"CHF per {row.get('original_currency') or 'unknown currency'}"
    if field in {'quantity', 'line_item_usage_amount'}:
        return row.get('unit') or row.get('unit_of_measure') or row.get('pricing_unit') or 'Unknown unit'
    if field in {'price_per_seat', 'price_per_licence'}:
        return row.get('currency') or 'Unknown currency'
    return field.replace('_', ' ')


def hist(values):
    low, high = min(values), max(values)
    if low == high:
        return [(str(low), len(values))]
    width = (high - low) / 8
    bins = Counter(min(7, int((value - low) / width)) for value in values)
    return [(f'{low + i * width:.5g} to {low + (i + 1) * width:.5g}', bins[i]) for i in range(8)]


def gaps(name, records, scope):
    spec = SPECS[f'{name}.csv']
    observed = defaultdict(set)
    if spec.cadence not in {'monthly', 'daily', 'weekly'}:
        return
    for record in records:
        row = record.row
        if not row.get('event_date'):
            continue
        cadence = row.get('observation_cadence') or spec.cadence
        entity = tuple(str(row.get(slug(field)) or '?') for field in spec.entity.split())
        if name == 'data_platform_usage':
            entity += (row.get('cluster') or '?',)
        day = date.fromisoformat(row['event_date'])
        if cadence == 'monthly':
            day = day.replace(day=1)
        observed[(entity, cadence)].add(day)
    if name in {'exchange_rates', 'business_calendar'} and not observed:
        observed[((), spec.cadence)] = set()
    for (entity, cadence), days in observed.items():
        if scope == 'baseline' and name in {'exchange_rates', 'business_calendar', 'data_platform_usage'}:
            lo, hi = START, END
        elif days:
            lo, hi = min(days), max(days)
        else:
            continue
        missing = sorted(set(period_sequence(lo, hi, cadence)) - days)
        if missing:
            yield dict(label=' / '.join(entity) or name, count=len(missing),
                       description=f'{cadence}: ' + ', '.join(day.isoformat() for day in missing))


def blank(value):
    return value is None or isinstance(value, str) and not value.strip()


def profiles(tables):
    result, issues = [], []
    for name, records in tables.items():
        spec = SPECS[f'{name}.csv']
        columns = {slug(field): field for field in spec.types}
        fields = list(dict.fromkeys([*columns, *(key for record in records for key in record.row)]))
        for scope in ('full', 'baseline'):
            source = [record for record in records if scope == 'full' or
                      record.row.get('baseline_overlap') or record.row.get('baseline_context')]
            accepted = [record for record in source if record.row['record_status'] == 'accepted']
            base = dict(table=name, scope=scope)
            keys = Counter(tuple(record.row.get(slug(field)) for field in spec.key.split()) for record in accepted)
            dates = sorted(record.row['event_date'] for record in accepted if record.row.get('event_date'))
            result.append(dict(**base, section='summary', bronze_rows=len(source), silver_rows=len(accepted),
                               minimum=dates[0] if dates else None, maximum=dates[-1] if dates else None,
                               count=sum(count == 1 for count in keys.values()),
                               description=f'Candidate key: {spec.key}. Baseline includes overlapping weeks and snapshot/master context.'))
            for gap in gaps(name, accepted, scope):
                result.append(dict(**base, section='gap', **gap))
                if scope == 'baseline':
                    issues.append(dict(source_file=f'{name}.csv', field=spec.date, code='observation_gaps',
                                       reason=f"{gap['label']}: {gap['description']}", impact='Observation coverage',
                                       next_investigation='Check the source export for missing observations.'))
            for field in fields:
                kind = field_type(name, field)
                origin = columns.get(field)
                valid = missing = optional = na = invalid = 0
                observed = set()
                groups = defaultdict(list)
                for record in accepted:
                    value = record.row.get(field)
                    if field in record.not_applicable:
                        na += 1
                    elif blank(value):
                        if field in OPTIONAL:
                            optional += 1
                        elif origin and not blank(record.raw[origin]):
                            invalid += 1
                        else:
                            missing += 1
                    else:
                        valid += 1
                        observed.add(type(value).__name__)
                        if isinstance(value, Decimal):
                            groups[measurement_label(record.row, name, field)].append(value)
                description = (f'Source field {origin} standardized using the Bronze data dictionary.'
                               if origin else f'Silver {field.replace("_", " ")}.')
                result.append(dict(**base, section='column', field=field, expected_type=kind,
                                   observed_type='/'.join(sorted(observed)) or 'empty', valid=valid,
                                   missing=missing, not_applicable=na, optional_blank=optional, invalid=invalid,
                                   description=description))
                if origin:
                    populations = defaultdict(lambda: [[], []])
                    for index, rows in enumerate((source, accepted)):
                        for record in rows:
                            label = measurement_label(record.row, name, field) if kind == 'decimal' else 'All records'
                            populations[label][index].append(record)
                    for label, (before, after) in populations.items():
                        result.append(dict(**base, section='comparison', field=field, label=label,
                                           bronze_rows=len(before), silver_rows=len(after),
                                           bronze_missing=sum(blank(r.raw[origin]) for r in before),
                                           matched_bronze_missing=sum(blank(r.raw[origin]) for r in after),
                                           missing=sum(blank(r.row.get(field)) for r in after),
                                           description='Blank counts include optional and non-applicable cells. Matched Bronze uses the same accepted source rows.'))
                for label, values in sorted(groups.items()):
                    result.append(dict(**base, section='distribution', field=field, label=label, count=len(values),
                                       minimum=min(values), median=median(values), mean=mean(values), maximum=max(values)))
                    for index, (interval, count) in enumerate(hist(values)):
                        result.append(dict(**base, section='histogram', field=field, label=label,
                                           bin=interval, count=count, valid=index))
    return result, issues
