"""Reconcile staged Silver facts and publish a validated current version."""
import argparse
import shutil
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from src.ingest import ROOT
from src.profile import END, START, read_csv
from src.silver_storage import (FINANCIAL, REPORTS, TABLES, atomic_csv, manifest,
                                pointer, silver_directory, validate, write_csv)

FILES = (*TABLES, *REPORTS, *FINANCIAL)
RECON_FIELDS = ('dimension', 'group', 'record_count', 'included', 'missing_amount', 'missing_fx',
                'draft', 'outside_baseline', 'duplicate', 'review', 'quarantined',
                'recorded_cost_chf', 'coverage_status', 'agrees_with_total')


def reconcile(facts):
    if len({row['record_id'] for row in facts}) != len(facts):
        raise ValueError('Cost facts contain repeated source record IDs')
    for row in facts:
        if row['financial_status'] not in RECON_FIELDS[3:11]:
            raise ValueError('Unexpected cost fact disposition')
        if row['financial_status'] == 'included' and (
                not row['cost_chf'] or not Decimal(row['cost_chf']).is_finite()
                or row['baseline_overlap'] != 'True' or row['baseline_eligible'] != 'True'):
            raise ValueError('Invalid included cost fact')
    dimensions = ('source_file', 'provider', 'reporting_month', 'reporting_department', 'currency')
    groups = defaultdict(list)
    for row in facts:
        for dimension in dimensions:
            groups[dimension, row[dimension] or 'Unknown'].append(row)

    def summarize(rows, dimension, group):
        count = Counter(row['financial_status'] for row in rows)
        subtotal = sum((Decimal(row['cost_chf']) for row in rows if row['financial_status'] == 'included'), Decimal(0))
        outstanding = any(
            row['financial_status'] in {'missing_amount', 'missing_fx'}
            or row['financial_status'] in {'review', 'quarantined'} and
            (row['baseline_overlap'] == 'True' or not row['event_date'])
            for row in rows
        )
        return dict(dimension=dimension, group=group, record_count=len(rows),
                    **{key: count[key] for key in RECON_FIELDS[3:11]}, recorded_cost_chf=subtotal,
                    coverage_status='incomplete' if outstanding or not count['included'] else 'recorded',
                    agrees_with_total=True)

    total = summarize(facts, 'total', 'All recorded charges')
    rows = [summarize(group, dimension, label) for (dimension, label), group in sorted(groups.items())]
    for dimension in dimensions:
        matching = [row for row in rows if row['dimension'] == dimension]
        for field in (*RECON_FIELDS[2:11], 'recorded_cost_chf'):
            if sum(row[field] for row in matching) != total[field]:
                raise ValueError(f'Reconciliation failed for {dimension}: {field}')
    return [total, *rows]


def publish(out):
    version = pointer(out, 'pending')
    source = out / '.silver-staging' / version
    snapshot, rules = validate(source, version, (*TABLES, *REPORTS))
    _, facts = read_csv(source / 'cost_facts.csv')
    rows = reconcile(facts)
    total = rows[0]
    baseline = [dict(silver_version=version, snapshot_id=snapshot, start=START, end=END,
                     recorded_cost_chf=total['recorded_cost_chf'], coverage_status=total['coverage_status'],
                     included=total['included'], missing_amount=total['missing_amount'], missing_fx=total['missing_fx'])]
    root = silver_directory(out)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / version
    with tempfile.TemporaryDirectory(dir=root) as temp:
        directory = Path(temp) / version
        shutil.copytree(source, directory)
        write_csv(directory / 'reconciliation_report.csv', rows, RECON_FIELDS)
        write_csv(directory / 'cost_baseline.csv', baseline)
        manifest(directory, version, snapshot, rules, FILES)
        validate(directory, version, FILES)
        if destination.exists():
            validate(destination, version, FILES)
            if (directory / 'manifest.csv').read_bytes() != (destination / 'manifest.csv').read_bytes():
                raise ValueError('Published version differs from the staged reconciliation')
        else:
            directory.rename(destination)
    for name in ('cost_baseline', 'reconciliation_report', 'unresolved_issues'):
        _, records = read_csv(destination / f'{name}.csv')
        if records:
            atomic_csv(out / f'{name}.csv', records)
        else:
            columns, _ = read_csv(destination / f'{name}.csv')
            atomic_csv(out / f'{name}.csv', records, columns)
    atomic_csv(out / 'current_silver.csv', [{'version': version}])
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    print(publish(args.out))


if __name__ == '__main__':
    main()
