import { tableCreation } from './journeyMetadata';
import { lazy, Suspense, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { components } from './api/schema';
import { CatalogRow, LayerDisclosure, LayerSummary } from './LayerOverview';
import { chfFormat as chf, formatCount as number, formatExactNumber } from './numberFormat';

const Chart = lazy(() => import('./AnalysisChart'));
type Models = components['schemas'];
type Overview = Models['SilverOverview'];
type Row = Models['Page']['items'][number];
type Scope = 'full' | 'baseline';
const labels = (value: string) => value.replaceAll('_', ' ');

const cleaningSteps: Partial<Record<string, string[]>> = {
  azure_costs: [
    'Parsed billing dates and JSON tags, then extracted the resource ID from the provider path.',
    'Standardized project and environment labels and linked resources to ownership records where the match was clear.',
    'Converted recorded charges to CHF using the matching monthly rate. Missing amounts stayed blank.',
  ],
  aws_costs: [
    'Parsed usage timestamps and extracted resource IDs from AWS resource names.',
    'Separated usage from fees, identified monthly charges and matched resource ownership where available.',
    'Converted recorded USD amounts using the monthly USD-to-CHF rate.',
  ],
  hoster_invoice: [
    'Parsed Swiss invoice dates and standardized project IDs.',
    'Linked invoice items to resources only when the item label matched exactly one record.',
    'Retained original CHF amounts and flagged ownership conflicts and missing charges.',
  ],
  data_platform_usage: [
    'Standardized observation dates and resource IDs and checked for repeated cluster-day records.',
    'Checked measurement ranges and calculated node-hours from node count and runtime.',
  ],
  server_inventory: [
    'Standardized server IDs, regions and project IDs and trimmed inventory tags.',
    'Labeled the inventory snapshot and its 30-day usage window, then matched owner departments where supported.',
  ],
  server_metrics_weekly: [
    'Checked week start dates and measurement ranges and identified weeks overlapping the baseline.',
    'Linked servers to inventory and used asset type to distinguish GPU readings that were missing from those that did not apply.',
  ],
  ai_usage: [
    'Standardized reporting dates, resource IDs, project IDs and model labels.',
    'Kept the consuming department separate from the resource owner.',
    'Derived uncached input tokens and carried recorded gateway costs forward in CHF.',
  ],
  ai_subscriptions: [
    'Standardized monthly contract records and retained Draft and Final versions.',
    'Checked active seats against purchased seats and reported amounts against seat prices.',
    'Converted recorded amounts to CHF. Only Final versions qualify for the cost baseline.',
  ],
  saas_contracts: [
    'Standardized billing months and retained Draft and Final versions.',
    'Checked seat counts and reported amounts, keeping the monthly amount even for annual billing.',
    'Converted recorded amounts to CHF. Only Final versions qualify for the cost baseline.',
  ],
  mapping_departments_tools: [
    'Standardized resource IDs and default project IDs.',
    'Checked mapping keys and flagged ambiguous departments and missing ownership.',
  ],
  exchange_rates: [
    'Standardized rate months and checked that recorded EUR and USD rates were positive.',
    'Checked for duplicate months and gaps. Currency conversion requires an unambiguous rate for the month.',
  ],
  it_tickets: [
    'Standardized ticket fields and parsed dates while preserving the original descriptions.',
    'Matched explicit resource mentions and flagged discrepancies with the ticket’s structured resource reference.',
  ],
  business_calendar: [
    'Parsed calendar dates and derived the month, quarter and ISO weekday.',
    'Checked the reported weekday against the date and flagged workdays that conflict with weekends or recorded holidays.',
  ],
};

async function read<T extends { version: string }>(path: string, signal: AbortSignal, version?: string): Promise<T> {
  const url = new URL('/api/v1/silver' + path, window.location.origin);
  if (version) url.searchParams.set('version', version);
  const response = await fetch(url, { signal });
  if (!response.ok) {
    const error = await response.json();
    throw Error(error.detail?.message ?? (typeof error.detail === 'string' ? error.detail : 'Silver request failed.'));
  }
  const payload = await response.json() as T;
  if (version && payload.version !== version) throw Error('Silver version changed. Reload the overview.');
  return payload;
}

function useSilver<T extends { version: string }>(version: string, path: string, enabled = true) {
  return useQuery({
    queryKey: ['silver', version, path],
    queryFn: ({ signal }) => read<T>(path, signal, version),
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}

function Result<T>({ query, children }: {
  query: { data?: T; isError: boolean; error: Error | null; refetch: () => unknown };
  children: (value: T) => ReactNode;
}) {
  if (query.isError) return <div className="error-panel" role="alert"><strong>Unavailable</strong>
    <p>{query.error?.message}</p><button onClick={() => void query.refetch()}>Try again</button></div>;
  if (!query.data) return <p role="status">Loading Silver data…</p>;
  return children(query.data);
}

function Section({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return <details className="panel analysis-section" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{title}</summary>
    {open && <div className="analysis-section-content">{children}</div>}
  </details>;
}

function Select({ label, value, options, onChange }: {
  label: string; value: string; options: [string, string][]; onChange: (value: string) => void;
}) {
  return <label>{label}<select value={value} onChange={event => onChange(event.target.value)}>
    {options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
  </select></label>;
}

function Grid({ rows, fields, choose }: { rows: Row[]; fields: string[]; choose?: (id: string) => void }) {
  if (!rows.length) return <p className="empty">No records match these filters.</p>;
  return <div className="table-scroll silver-scroll" tabIndex={0}><table>
    <thead><tr>{choose && <th scope="col">Lineage</th>}{fields.map(field => <th key={field} scope="col">{labels(field)}</th>)}</tr></thead>
    <tbody>{rows.map((row, index) => <tr key={index}>
      {choose && <td>{row.record_id && <button onClick={() => choose(String(row.record_id))}>Inspect row {row.source_row}</button>}</td>}
      {fields.map(field => {
        const value = row[field];
        return <td key={field}>{value == null || value === '' ? '—' :
          typeof value === 'number' ? formatExactNumber(value) : String(value)}</td>;
      })}
    </tr>)}</tbody>
  </table></div>;
}

function Pagination({ page, setOffset }: { page: Models['Page']; setOffset: (offset: number) => void }) {
  return <div className="pagination">
    <button disabled={!page.offset} onClick={() => setOffset(page.offset - page.limit)}>Previous</button>
    <span>{page.total ? `${number(page.offset + 1)}–${number(Math.min(page.total, page.offset + page.limit))} of ${number(page.total)}` : '0 records'}</span>
    <button disabled={page.offset + page.limit >= page.total} onClick={() => setOffset(page.offset + page.limit)}>Next</button>
  </div>;
}

export default function Silver({ initialTable }: { initialTable?: string }) {
  const overview = useQuery({
    queryKey: ['silver', 'current'],
    queryFn: ({ signal }) => read<Overview>('', signal),
    retry: false,
  });
  return <div className="layer-dashboard">
    <header className="layer-heading">
      <h1>Silver overview</h1>
      <p>Cleaned data linked back to its original sources.</p>
    </header>
    <Result query={overview}>{data => <SilverDetails key={data.version} data={data} initialTable={data.tables.find(table => table.table === initialTable)?.table} />}</Result>
  </div>;
}

function SilverDetails({ data, initialTable }: { data: Overview; initialTable?: string }) {
  const [scope, setScope] = useState<Scope>('full');
  const [record, setRecord] = useState('');
  const [lineageOpen, setLineageOpen] = useState(false);

  function inspect(id: string) {
    setRecord(id);
    setLineageOpen(true);
  }

  return <>
    <LayerSummary label="Silver build summary" metrics={[
      { label: 'Recorded-cost subtotal', value: chf.format(Number(data.recorded_cost_chf)), note: `${data.baseline_start} to ${data.baseline_end}` },
      { label: 'Tables produced', value: number(data.tables.length) },
      { label: 'Accepted source records', value: number(data.accepted) },
    ]}>
      <div className="layer-summary-status">
        <strong>{data.status}</strong>
        <span>{data.coverage_status === 'incomplete' ? 'Financial coverage is incomplete.' : 'Recorded financial coverage.'}
          {data.issues > 0 && ` ${number(data.issues)} unresolved findings.`}</span>
      </div>
    </LayerSummary>
    <div className="layer-actions">
      <LayerDisclosure title="Browse Silver tables" description="Review cleaning steps for source tables and why each new table was created.">
        {() => <SilverCatalog tables={data.tables} />}
      </LayerDisclosure>
      <LayerDisclosure defaultOpen={!!initialTable} title="Explore data and costs" description="Inspect rows, compare with Bronze and reconcile the cost subtotal.">
        {open => open && <section className="exploration" aria-label="Silver data and cost analysis">
          <div className="analysis-toolbar">
            <div className="segmented" aria-label="Silver analysis period">
              {(['full', 'baseline'] as const).map(value => <button key={value} aria-pressed={scope === value}
                onClick={() => setScope(value)}>{value === 'full' ? 'Full exports' : 'Baseline period'}</button>)}
            </div>
            <p>Baseline includes inventory snapshot context and full overlapping weeks.</p>
          </div>
          <div className="analysis-sections">
            <Section title="Cleaned table browser" defaultOpen={!!initialTable}><Browser key={scope} initialTable={initialTable} data={data} scope={scope} inspect={inspect} /></Section>
            <details className="panel analysis-section" open={lineageOpen} onToggle={event => setLineageOpen(event.currentTarget.open)}>
              <summary>Lineage and evidence</summary>
              {lineageOpen && <div className="analysis-section-content"><Lineage version={data.version} record={record} select={setRecord} /></div>}
            </details>
            <Section title="Unresolved issues"><Issues data={data} inspect={inspect} /></Section>
            <Section title="Financial reconciliation"><Reconciliation version={data.version} /></Section>
            <Section title="What changed from Bronze">
              <p>{number(data.field_changes)} field-level changes. Date counts also include validated ISO values.</p>
              <Grid fields={['rule', 'audit_entries']} rows={Object.entries(data.rules).sort().map(([rule, count]) => ({ rule, audit_entries: count }))} />
            </Section>
            <Section title="Profiling"><Profiles data={data} scope={scope} mode="profile" /></Section>
            <Section title="Distributions"><Profiles data={data} scope={scope} mode="distribution" /></Section>
            <Section title="Before versus after"><Profiles data={data} scope={scope} mode="comparison" /></Section>
            <Section title="Build information">
              <p>Build <code>{data.version}</code></p>
              <p>Bronze snapshot <code>{data.snapshot_id}</code></p>
              <p>{number(data.review)} records await review · {number(data.duplicates)} duplicate exclusions · {number(data.quarantined)} quarantined records.</p>
              <p>Inventory snapshot dated 2026-09-06. Unresolved findings can overlap across records.</p>
            </Section>
          </div>
        </section>}
      </LayerDisclosure>
    </div>
  </>;
}

function SilverCatalog({ tables }: { tables: Overview['tables'] }) {
  const groups = [
    { title: 'Cleaned source tables', tables: tables.filter(table => !tableCreation[table.table]) },
    { title: 'New tables', tables: tables.filter(table => tableCreation[table.table]) },
  ];

  return <div className="silver-catalog" aria-label="Silver table catalog">
    {groups.map(group => <section className="silver-catalog-group" key={group.title} aria-label={group.title}>
      <h2>{group.title}</h2>
      <ul className="layer-catalog silver-catalog-list">
        {group.tables.map(table => {
          const creation = tableCreation[table.table];
          const steps = cleaningSteps[table.table];
          return <CatalogRow key={table.table} name={`${table.table}.csv`}
            records={`${number(table.accepted)} / ${number(table.total)} accepted`}
            findings={table.issue_count ? `${number(table.issue_count)} issues` : 'No unresolved issues'}>
            {creation ? <>
              <h3>Why this table was created</h3>
              <p>{creation.reason}</p>
              <h3>How this table was created</h3>
              <p>{creation.method}</p>
              <h4>Cleaned Silver inputs</h4>
              <ul className="silver-inputs" aria-label="Cleaned Silver inputs">
                {creation.inputs.map(input => <li key={input}><code>{input}.csv</code></li>)}
              </ul>
            </> : <>
              <h3>Cleaning steps</h3>
              {steps ? <ul className="cleaning-steps">{steps.map(step => <li key={step}>{step}</li>)}</ul> : <p>{table.purpose}</p>}
            </>}
            {!!table.limitations.length && <><h3>Unresolved findings</h3>
              <ul>{table.limitations.map(item => <li key={item}>{item}</li>)}</ul></>}
            {!!Object.keys(table.transformations ?? {}).length && <details className="profile-index">
              <summary>Transformation audit entries</summary>
              <dl className="catalog-findings">{Object.entries(table.transformations).map(([rule, count]) =>
                <div key={rule}><dt>{labels(rule)}</dt><dd>{number(count)}</dd></div>)}</dl>
            </details>}
          </CatalogRow>;
        })}
      </ul>
    </section>)}
  </div>;
}

function Browser({ data, scope, inspect, initialTable }: { data: Overview; scope: Scope; inspect: (id: string) => void; initialTable?: string }) {
  const [table, setTable] = useState(initialTable ?? data.tables[0].table);
  const [status, setStatus] = useState('accepted');
  const [offset, setOffset] = useState(0);
  const query = useSilver<Models['TablePage']>(data.version, `/tables/${table}/rows?scope=${scope}&status=${status}&offset=${offset}`);
  return <>
    <div className="source-controls">
      <Select label="Cleaned table" value={table} options={data.tables.map(t => [t.table, labels(t.table)])}
        onChange={value => { setTable(value); setOffset(0); }} />
      <Select label="Record status" value={status} options={['accepted', 'review', 'duplicate', 'quarantined', 'all'].map(v => [v, v])}
        onChange={value => { setStatus(value); setOffset(0); }} />
    </div>
    <Result query={query}>{page => <>
      <details><summary>Column descriptions</summary><Grid fields={['column', 'type', 'description']}
        rows={Object.entries(page.columns).map(([column, type]) => ({ column, type,
          description: column === 'source_row' ? 'Logical Bronze CSV record number, with header at 1.'
            : column === 'duplicate_of' ? 'Record ID of the retained original.'
            : column === 'baseline_overlap' ? 'Observation overlaps the official baseline.'
            : column === 'record_status' ? 'Disposition used by the default analytical views.'
            : labels(column) }))} /></details>
      <Grid rows={page.items} fields={Object.keys(page.columns)} choose={page.columns.source_row ? inspect : undefined} />
      <Pagination page={page} setOffset={setOffset} />
    </>}</Result>
  </>;
}

function Profiles({ data, scope, mode }: { data: Overview; scope: Scope; mode: 'profile' | 'distribution' | 'comparison' }) {
  const [table, setTable] = useState(data.tables[0].table);
  const query = useSilver<Models['TableProfile']>(data.version, `/tables/${table}/profile?scope=${scope}`);
  return <>
    <Select label="Profile source" value={table} options={data.tables.slice(0, 13).map(t => [t.table, labels(t.table)])} onChange={setTable} />
    <Result query={query}>{profile => {
      const section = (name: string) => profile.items.filter(row => row.section === name);
      if (mode === 'distribution') return <Distribution key={table + scope} groups={section('distribution')} bins={section('histogram')} />;
      if (mode === 'comparison') return <>
        <p>Compare each field within the selected source, period and unit. Silver uses accepted rows. Matched Bronze counts use those same rows, so excluded records cannot be mistaken for recovered data.</p>
        <Grid rows={section('comparison')} fields={['field', 'label', 'bronze_rows', 'silver_rows', 'bronze_missing', 'matched_bronze_missing', 'missing']} />
      </>;
      return <>
        <Grid rows={section('summary')} fields={['bronze_rows', 'silver_rows', 'minimum', 'maximum', 'count', 'description']} />
        <Grid rows={section('column')} fields={['field', 'expected_type', 'observed_type', 'valid', 'missing', 'not_applicable', 'optional_blank', 'invalid', 'description']} />
        <details><summary>Observation gaps</summary><Grid rows={section('gap')} fields={['label', 'count', 'description']} /></details>
      </>;
    }}</Result>
  </>;
}

function Distribution({ groups, bins }: { groups: Row[]; bins: Row[] }) {
  const [index, setIndex] = useState(0);
  const selected = groups[index];
  if (!selected) return <p className="empty">No numeric measurements in this view.</p>;
  return <>
    <Select label="Silver measurement" value={String(index)} options={groups.map((group, i) =>
      [String(i), `${labels(String(group.field))} · ${group.label}`])} onChange={value => setIndex(Number(value))} />
    <Grid rows={[selected]} fields={['count', 'minimum', 'median', 'mean', 'maximum']} />
    <Suspense fallback={<p>Loading histogram…</p>}>
      <Chart horizontal={false} data={bins.filter(row => row.field === selected.field && row.label === selected.label)
        .map(row => ({ name: String(row.bin), value: Number(row.count) }))} />
    </Suspense>
  </>;
}

function Lineage({ version, record, select }: { version: string; record: string; select: (id: string) => void }) {
  const [input, setInput] = useState('');
  const query = useSilver<Models['Lineage']>(version, `/records/${encodeURIComponent(record)}`, !!record);
  return <>
    <form className="source-controls" onSubmit={event => { event.preventDefault(); select(input.trim()); }}>
      <label>Silver record ID<input value={input} onChange={event => setInput(event.target.value)} /></label>
      <button type="submit">Find record</button>
    </form>
    {!record ? <p>Inspect a row in the cleaned table browser or enter its record ID.</p> :
      <Result query={query}>{lineage => <>
        <p><strong>{lineage.record.source_file}</strong> · Bronze logical row {lineage.record.source_row} · {lineage.record.record_status}</p>
        <p>{lineage.record.status_reason} <code>{record}</code></p>
        {lineage.record.duplicate_of && <button onClick={() => select(String(lineage.record.duplicate_of))}>Inspect retained original</button>}
        <Grid rows={lineage.changes} fields={['field', 'original_value', 'cleaned_value', 'rule', 'reason', 'evidence_record_id']} />
        {!!lineage.issues.length && <Grid rows={lineage.issues} fields={['code', 'reason', 'next_investigation']} />}
      </>}</Result>}
  </>;
}

function Reconciliation({ version }: { version: string }) {
  const [dimension, setDimension] = useState('source_file');
  const [offset, setOffset] = useState(0);
  const query = useSilver<Models['Page']>(version, `/reconciliation?dimension=${dimension}&offset=${offset}`);
  return <>
    <p>Grouped recorded CHF subtotals reconcile to the same total. Missing costs and FX remain unknown.</p>
    <Select label="Group costs by" value={dimension} options={[
      ['source_file', 'Source'], ['provider', 'Provider'], ['reporting_month', 'Month'],
      ['reporting_department', 'Owner department'], ['currency', 'Original currency'], ['total', 'Total'],
    ]} onChange={value => { setDimension(value); setOffset(0); }} />
    <Result query={query}>{page => <>
      <Grid rows={page.items.map(row => ({ ...row, recorded_cost_chf: chf.format(Number(row.recorded_cost_chf)) }))}
        fields={['group', 'record_count', 'included', 'missing_amount', 'missing_fx', 'draft', 'outside_baseline',
          'duplicate', 'review', 'quarantined', 'recorded_cost_chf', 'coverage_status', 'agrees_with_total']} />
      <Pagination page={page} setOffset={setOffset} />
    </>}</Result>
  </>;
}

function Issues({ data, inspect }: { data: Overview; inspect: (id: string) => void }) {
  const [source, setSource] = useState('');
  const [code, setCode] = useState('');
  const [offset, setOffset] = useState(0);
  const query = useSilver<Models['Page']>(data.version, `/issues?source=${source}&code=${code}&offset=${offset}`);
  return <>
    <div className="source-controls">
      <Select label="Issue source" value={source} options={[[ '', 'All sources' ], ...data.tables.slice(0, 13).map(
        (item): [string, string] => [item.table, labels(item.table)])]} onChange={value => { setSource(value); setOffset(0); }} />
      <Select label="Issue code" value={code} options={[[ '', 'All issues' ], ...data.issue_codes.map(
        (item): [string, string] => [item, labels(item)])]} onChange={value => { setCode(value); setOffset(0); }} />
    </div>
    <Result query={query}>{page => <>
      <Grid rows={page.items} fields={['source_file', 'source_row', 'field', 'code', 'reason', 'impact', 'next_investigation']} choose={inspect} />
      <Pagination page={page} setOffset={setOffset} />
    </>}</Result>
  </>;
}
