import { lazy, Suspense, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analysis, analysisBase, readJson, type Chart, type Lineage, type Result } from './api/analysis';
import { formatCount, formatExactNumber, isNumericColumn } from './numberFormat';

const ResultChart = lazy(() => import('./ResultChart'));

function Evidence({ record, version }: { record: string; version: string }) {
  const query = useQuery({
    queryKey: ['analysis-lineage', version, record],
    queryFn: () => readJson<Lineage>(`/api/v1/silver/records/${encodeURIComponent(record)}?version=${encodeURIComponent(version)}`),
  });
  const lineage = query.data;
  if (!lineage) return <p role={query.isError ? 'alert' : 'status'}>{query.error?.message ?? 'Loading source evidence…'}</p>;
  return <div className="scope-note">
    <strong>{lineage.record.source_file}</strong> · Bronze row {lineage.record.source_row} · {lineage.record.record_status}
    <p>{lineage.record.status_reason} <code>{record}</code></p>
    {!!lineage.changes.length && <ul>{lineage.changes.map((change, index) => <li key={index}>
      {change.field} · {change.original_value ?? 'null'} → {change.cleaned_value ?? 'null'} · {change.reason}
    </li>)}</ul>}
    {!!lineage.issues.length && <ul>{lineage.issues.map((issue, index) => <li key={index}>{issue.code} · {issue.message ?? issue.reason}</li>)}</ul>}
  </div>;
}

export default function AnalysisResults({ initial, stale, chart, onChart }: {
  initial: Result; stale: boolean; chart: Chart; onChart: (chart: Chart) => void;
}) {
  const { metadata } = initial;
  const [offset, setOffset] = useState(0);
  const [record, setRecord] = useState('');
  const [mode, setMode] = useState<'table' | 'chart'>('table');
  const query = useQuery({
    queryKey: ['analysis-page', metadata.id, offset],
    queryFn: () => analysis<Result>(`/results/${metadata.id}?offset=${offset}`),
    enabled: offset > 0,
    staleTime: Infinity,
  });
  const page = offset === 0 ? initial : query.data;
  const exportBase = `${analysisBase}/results/${metadata.id}`;
  const { missing_amount: missingAmount, missing_fx: missingFx, included } = metadata.coverage;
  const financialCoverage = included !== undefined || missingAmount !== undefined || missingFx !== undefined;

  return <section className="panel workspace-results" aria-label="Analysis results">
    <div className="workspace-results-heading">
      <div><h2>Results</h2><p>{formatCount(metadata.row_count)} rows · {formatExactNumber(metadata.elapsed_ms)} ms · <code>{metadata.dataset}</code></p></div>
      <div className="workspace-actions">
        <a className="workspace-button" href={`${exportBase}/csv`}>Export CSV</a>
        <a className="workspace-button" href={`${exportBase}/metadata`}>Export metadata</a>
      </div>
    </div>
    {financialCoverage && <p className="scope-note">
      Scoped cost coverage · {formatCount((missingAmount ?? 0) + (missingFx ?? 0))} rows missing an amount or FX.
      Coverage is measured before query filters.
    </p>}
    {stale && <p className="workspace-stale" role="status">Definition changed. These results are from the last successful run.</p>}
    {(metadata.truncated || metadata.requested_limit) && <p className="scope-note">
      {metadata.truncated ? `Result truncated to ${formatCount(metadata.materialization_limit)} rows. ` : ''}
      {metadata.requested_limit ? `Query limit ${formatCount(metadata.requested_limit)} rows.` : ''}
    </p>}
    <div className="segmented workspace-modes">
      <button aria-pressed={mode === 'table'} onClick={() => setMode('table')}>Table</button>
      <button aria-pressed={mode === 'chart'} onClick={() => setMode('chart')}>Chart</button>
    </div>
    {mode === 'chart' ? <Suspense fallback={<p role="status">Loading chart…</p>}>
      <ResultChart result={initial} chart={chart} update={onChart} />
    </Suspense> : <>
      {query.isError && <p role="alert" className="error-panel">{query.error.message}</p>}
      {page ? <div className="table-scroll silver-scroll" tabIndex={0} aria-label="Query result table">
        <table>
          <thead><tr>{metadata.fields.map((field, index) => <th key={index} scope="col">
            {field.name}<small>{field.type}{field.unit ? ` · ${field.unit}` : ''}</small>
          </th>)}</tr></thead>
          <tbody>{page.rows.map((row, index) => <tr key={index}>{row.map((value, column) => <td key={column}>
            {value != null && metadata.lineage_field === metadata.fields[column].name
              ? <button className="source-link" onClick={() => setRecord(String(value))}>View lineage <code>{String(value)}</code></button>
              : value == null ? <span className="muted">null</span> :
                isNumericColumn(metadata.fields[column].type) ? formatExactNumber(String(value)) : String(value)}
          </td>)}</tr>)}</tbody>
        </table>
        {!page.rows.length && <p className="empty">No matching rows</p>}
      </div> : query.isFetching && <p role="status">Loading result page…</p>}
      <div className="pagination">
        <button disabled={!offset} onClick={() => setOffset(offset - 100)}>Previous</button>
        <span>{formatCount(metadata.row_count ? offset + 1 : 0)}–{formatCount(Math.min(offset + 100, metadata.row_count))} of {formatCount(metadata.row_count)}</span>
        <button disabled={offset + 100 >= metadata.row_count} onClick={() => setOffset(offset + 100)}>Next</button>
      </div>
    </>}
    {record && <details open key={record} className="workspace-evidence"><summary>Record lineage</summary>
      <Evidence record={record} version={metadata.version} /></details>}
    <details className="workspace-evidence">
      <summary>Quality, coverage and query provenance</summary>
      <p>Silver version <code>{metadata.version}</code></p>
      <p>Applied scope · {metadata.filters.period} · {metadata.filters.disposition} · {metadata.filters.financial} costs</p>
      <p>{formatCount(metadata.dataset_rows)} scoped dataset rows before query filters.</p>
      {!!Object.keys(metadata.coverage).length && <dl className="workspace-coverage">
        {Object.entries(metadata.coverage).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{formatCount(value)}</dd></div>)}
      </dl>}
      <pre>{metadata.sql}</pre>
    </details>
  </section>;
}
