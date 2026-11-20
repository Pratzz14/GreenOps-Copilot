"""Deterministic CSV storage and validation for the Silver build."""
import csv
import hashlib
import os
import re
import tempfile
from itertools import chain
from pathlib import Path

from src.ingest import CORE_FILES, ROOT
from src.profile import read_csv

SOURCE_TABLES = tuple(Path(name).stem for name in CORE_FILES)
TABLES = (*SOURCE_TABLES, 'cost_facts', 'usage_facts', 'assets', 'contracts',
          'ownership', 'resource_relationships')
REPORTS = ('transformation_log', 'profiles', 'unresolved_issues')
FINANCIAL = ('cost_baseline', 'reconciliation_report')
VERSION_PATTERN = re.compile(r'[a-f0-9]{64}')


def silver_directory(out):
    """Use the layered project data directory and keep custom runs self-contained."""
    return ROOT / 'data' / 'silver' if out.resolve() == ROOT / 'outputs' else out / 'silver'


def file_hash(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_csv(path, rows, columns=()):
    columns = list(dict.fromkeys(chain(columns, (key for row in rows for key in row))))
    if not columns:
        raise ValueError(f'Missing schema for {path.name}')
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def atomic_csv(path, rows, columns=()):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        write_csv(temporary, rows, columns)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def pointer(out, name):
    _, rows = read_csv(out / f'{name}_silver.csv', ('version',))
    if len(rows) != 1 or not VERSION_PATTERN.fullmatch(rows[0]['version']):
        raise ValueError('Invalid Silver version pointer')
    return rows[0]['version']


def manifest(directory, version, snapshot, rules, names):
    write_csv(directory / 'manifest.csv', [
        dict(version=version, snapshot_id=snapshot, rules_hash=rules, artifact=f'{name}.csv',
             sha256=file_hash(directory / f'{name}.csv'))
        for name in names
    ])


def validate(directory, version, names, snapshot=None):
    _, entries = read_csv(directory / 'manifest.csv',
                          ('version', 'snapshot_id', 'rules_hash', 'artifact', 'sha256'))
    expected = {f'{name}.csv' for name in names}
    if len(entries) != len(expected) or {entry['artifact'] for entry in entries} != expected:
        raise ValueError('Incomplete Silver manifest')
    identity = { (entry['version'], entry['snapshot_id'], entry['rules_hash']) for entry in entries }
    if len(identity) != 1:
        raise ValueError('Inconsistent Silver manifest identity')
    actual, bronze, rules = identity.pop()
    if (actual != version or not all(VERSION_PATTERN.fullmatch(v) for v in (actual, bronze, rules))
            or hashlib.sha256(f'{bronze}:{rules}'.encode()).hexdigest() != version
            or (snapshot is not None and snapshot != bronze)):
        raise ValueError('Silver manifest does not match the requested snapshot or version')
    for entry in entries:
        if file_hash(directory / entry['artifact']) != entry['sha256']:
            raise ValueError(f"Silver hash mismatch for {entry['artifact']}")
    return bronze, rules
