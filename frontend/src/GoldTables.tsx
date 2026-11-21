import { purpose } from './journeyMetadata';
import { useState } from 'react';
import { useGold } from './api/gold';
import type { components } from './api/schema';
import { CatalogRow, LayerDisclosure } from './LayerOverview';
import { formatCount, formatExactNumber, isNumericColumn } from './numberFormat';

type Models = components['schemas'];
const pageSize = 25;
const supportingFields = ['subject_id', 'evidence_set_id', 'run_id'];
const tableDetails: Record<string, [grain: string, inputs: string]> = {
  analysis_run: ['Published Gold run', 'Silver snapshot, decision date, factor registry, and case targets'],
  subject: ['Reporting resource, instance, product, service, or unresolved bucket', 'Silver assets, contracts, ownership, and resource links'],
  cost_monthly: ['Month, subject, provider, department, tool, location, and billing stream', 'Silver cost facts, billing geography, and ownership'],
  impact_monthly: ['Month, subject, provider, department, tool, location, workload boundary, and scenario', 'Silver activity records and Gold energy and grid factors'],
  factor: ['Versioned factor or assumption', 'Grid references, energy benchmarks, and allocation assumptions'],
  licence_monthly: ['Final contract and reporting month', 'Silver contracts and monthly exchange rates'],
  finding: ['Evidence-backed waste hypothesis', 'Silver usage, contracts, costs, and assets'],
  protection_window: ['Subject and concrete protection interval or standing restriction', 'Silver tickets, business calendar, inventory, and ownership'],
  measure: ['Candidate action', 'Findings, protections, contract terms, and effort assumptions'],
  measure_scenario: ['Measure, assumption scenario, and savings horizon', 'Modeled activity, prices, effective dates, and Gold factors'],
  measure_constraint: ['Measure pair and constraint type', 'Shared workloads, dependencies, and operational prerequisites'],
  package_result: ['Package, assumption scenario, and savings horizon', 'Gold baseline, selected measures, and optimization results'],
  package_member: ['Package, assumption scenario, savings horizon, and selected measure', 'Package results and credited measure contributions'],
  evidence: ['Evidence item within an evidence set', 'Source row references, tickets, factors, and calculation notes'],
};

function GoldTableRows({ runId, table }: { runId: string; table: string }) {
  const [offset, setOffset] = useState(0);
  const query = useGold<Models['GoldTablePage']>(`/runs/${runId}/tables/${table}?offset=${offset}&limit=${pageSize}`);
  const page = query.data;
  const columns = page ? [
    ...page.columns.filter(column => !supportingFields.includes(column.name)),
    ...page.columns.filter(column => supportingFields.includes(column.name)),
  ] : [];
  const [grain, inputs] = tableDetails[table] ?? [];
  const numericFields = new Set(columns.filter(column => isNumericColumn(column.type))
    .map(column => column.name));

  return <>
    <p className="gold-coverage">{purpose[table]}</p>
    {grain && inputs ? <dl className="gold-table-details">
      <div><dt>One row per</dt><dd>{grain}</dd></div>
      <div><dt>Data used</dt><dd>{inputs}</dd></div>
    </dl> : null}
    {query.isError ? <p role="alert">{query.error.message}</p> : !page ?
      <p role="status">Loading table rows…</p> : <>
        <details className="gold-evidence">
          <summary>Column schema</summary>
          <ul className="gold-table-schema">{page.columns.map(column => <li key={column.name}>
            <code>{column.name}</code> <small>{column.type}{column.primary_key ? ' · Primary key' : ''}</small>
          </li>)}</ul>
        </details>
        {page.items.length ? <div className="table-scroll gold-raw-table" tabIndex={0} aria-label={`${table} records`}>
          <table className="gold-table" aria-label={table}>
            <thead><tr>{columns.map(column => <th scope="col" key={column.name}>{column.name}</th>)}</tr></thead>
            <tbody>{page.items.map((row, index) => <tr key={page.offset + index}>
              {columns.map(({ name }) => {
                const value = row[name];
                return <td key={name}>{value == null ? <span className="muted">NULL</span> :
                  numericFields.has(name) ? formatExactNumber(value) : value}</td>;
              })}
            </tr>)}</tbody>
          </table>
        </div> : <p className="empty">No rows in this table for this run.</p>}
        {page.row_count > 0 ? <div className="pagination" aria-label="Table pagination">
          <button type="button" disabled={page.offset === 0} onClick={() => setOffset(page.offset - page.limit)}>Previous</button>
          <span aria-live="polite">{formatCount(page.offset + 1)}–{formatCount(page.offset + page.items.length)} of {formatCount(page.row_count)}</span>
          <button type="button" disabled={page.offset + page.limit >= page.row_count} onClick={() => setOffset(page.offset + page.limit)}>Next</button>
        </div> : null}
      </>}
  </>;
}

export default function GoldTables({ runId, initialTable }: { runId: string; initialTable?: string }) {
  const catalog = useGold<Models['GoldTableCatalog']>(`/runs/${runId}/tables`);
  const tables = catalog.data?.tables;
  const description = tables ? `${formatCount(tables.length)} tables in this run. Expand a table to see its schema and records.` :
    'Expand a table to see its schema and records.';
  return <LayerDisclosure title="Browse Gold tables" description={description} defaultOpen>
    {open => catalog.isError ? <p role="alert">{catalog.error.message}</p> : !tables ?
      <p role="status">Loading table catalog…</p> :
      <ul className="layer-catalog" aria-label="Published Gold tables">
        {tables.map(({ name, row_count }) => <CatalogRow key={name}
          name={name} defaultOpen={name === initialTable} records={`${formatCount(row_count)} ${row_count === 1 ? 'row' : 'rows'}`}>
          {() => open ? <GoldTableRows runId={runId} table={name} /> : null}
        </CatalogRow>)}
      </ul>}
  </LayerDisclosure>;
}
