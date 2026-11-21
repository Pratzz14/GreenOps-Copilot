import { useLayoutEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useGold } from './api/gold';
import { readQuality, type QualityOverview } from './api/quality';
import type { components } from './api/schema';
import { purpose, tableCreation } from './journeyMetadata';
import { formatCount } from './numberFormat';
import './dataJourney.css';

type Models = components['schemas'];
const layers = ['bronze', 'silver', 'gold'] as const;
type Layer = typeof layers[number];
type Table = { id: string; layer: Layer; name: string; description: string; rows: number; issues?: number; version: string; changes?: Record<string, number> };
type Edge = [string, string];
const names = { bronze: 'Bronze', silver: 'Silver', gold: 'Gold' };
const defaultTable = 'gold:cost_monthly';
const selectableLayers = ['silver', 'gold'] as const;
const goldInputs: Record<string, string[]> = {
  subject: ['silver:assets', 'silver:ownership', 'silver:contracts'],
  cost_monthly: ['silver:cost_facts', 'gold:subject'],
  impact_monthly: ['silver:azure_costs', 'silver:aws_costs', 'silver:hoster_invoice', 'silver:cost_facts', 'silver:data_platform_usage', 'silver:ai_usage', 'silver:contracts', 'gold:factor', 'gold:subject'],
  licence_monthly: ['silver:contracts', 'gold:subject'],
  finding: ['silver:contracts', 'silver:assets', 'silver:server_metrics_weekly', 'silver:data_platform_usage', 'silver:azure_costs', 'silver:ai_usage', 'gold:subject'],
  protection_window: ['silver:it_tickets', 'silver:business_calendar', 'gold:subject'],
  measure: ['gold:finding', 'gold:subject', 'gold:protection_window'],
  measure_scenario: ['gold:measure', 'gold:factor'],
  measure_constraint: ['gold:measure'],
  package_result: ['gold:measure_scenario', 'gold:measure_constraint', 'gold:cost_monthly', 'gold:impact_monthly'],
  package_member: ['gold:package_result', 'gold:measure'],
};
const tableUrl = (table: Table, inspect = false) => '/data-explorer?' + new URLSearchParams(
  inspect ? { view: table.layer, table: table.id } : { table: table.id },
);

function Lineage({ tables, edges, selection }: {
  tables: Table[]; edges: Edge[]; selection: Table;
}) {
  const canvas = useRef<HTMLDivElement>(null);
  const [paths, setPaths] = useState<string[]>([]);
  useLayoutEffect(() => {
    const root = canvas.current;
    if (!root) return;
    const draw = () => {
      const bounds = root.getBoundingClientRect();
      const cards = new Map([...root.querySelectorAll<HTMLElement>('[data-node]')]
        .map(card => [card.dataset.node, card.getBoundingClientRect()]));
      setPaths(edges.flatMap(([from, to]) => {
        const a = cards.get(from), b = cards.get(to);
        if (!a || !b) return [];
        if (Math.abs(a.left - b.left) < 1) {
          const x = a.left - bounds.left + a.width / 2;
          const start = (a.top < b.top ? a.bottom : a.top) - bounds.top;
          const end = (a.top < b.top ? b.top : b.bottom) - bounds.top;
          return [`M ${x} ${start} V ${end}`];
        }
        const x = a.right - bounds.left, end = b.left - bounds.left;
        const y = a.top - bounds.top + a.height / 2, target = b.top - bounds.top + b.height / 2;
        const mid = (x + end) / 2;
        return [`M ${x} ${y} C ${mid} ${y}, ${mid} ${target}, ${end} ${target}`];
      }));
    };
    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(root);
    return () => observer.disconnect();
  }, [edges]);

  function card(table: Table) {
    const content = <>
      <strong>{table.name}</strong><span>{table.description}</span>
      <small>{formatCount(table.rows)} records{table.issues ? ` · ${formatCount(table.issues)} issues` : ''}</small>
    </>;
    return table.id === selection.id
      ? <div key={table.id} className="journey-node journey-selected" data-node={table.id} aria-current="true">{content}</div>
      : <a key={table.id} className="journey-node" data-node={table.id} href={tableUrl(table, true)}>{content}</a>;
  }
  return <>
    <div className="journey-graph" ref={canvas}>
      <svg aria-hidden="true"><defs><marker id="journey-arrow" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" /></marker></defs>
        {paths.map((path, i) => <path key={i} d={path} markerEnd="url(#journey-arrow)" />)}
      </svg>
      {([selection.layer === 'silver' ? 'bronze' : 'silver', selection.layer] as const).map(layer => <section className={`journey-column ${layer}`} key={layer} aria-label={names[layer] + ' lineage'}>
        <h3>{names[layer]}</h3>
        {tables.some(table => table.layer === layer) ? tables.filter(table => table.layer === layer).map(card) : <p>No documented inputs in this layer.</p>}
      </section>)}
    </div>
  </>;
}

export default function DataJourney() {
  const bronze = useQuery({ queryKey: ['quality', 'full'], queryFn: ({ signal }) => readQuality<QualityOverview>('?scope=full', signal) });
  const silver = useQuery({ queryKey: ['silver', 'current'], queryFn: async ({ signal }) => {
    const response = await fetch('/api/v1/silver', { signal });
    if (!response.ok) throw new Error('The published Silver overview is unavailable.');
    return await response.json() as Models['SilverOverview'];
  } });
  const run = useGold<Models['GoldRun']>('/runs/current');
  const runPath = `/runs/${run.data?.run_id}`;
  const gold = useGold<Models['GoldTableCatalog']>(runPath + '/tables', !!run.data);
  const measures = useGold<Models['GoldMeasure'][]>(runPath + '/measures', !!run.data);
  const [selected, setSelected] = useState(() => new URLSearchParams(window.location.search).get('table') ?? defaultTable);
  const tables: Table[] = [
    ...(bronze.data?.sources.map(source => ({
      id: 'bronze:' + source.name, layer: 'bronze' as const, name: source.name, description: source.role,
      rows: source.rows, issues: Object.values(source.issue_counts).reduce((sum, count) => sum + count, 0),
      version: bronze.data!.snapshot_id,
    })) ?? []),
    ...(silver.data?.tables.map(table => ({
      id: 'silver:' + table.table, layer: 'silver' as const, name: table.table, description: table.purpose,
      rows: table.total, issues: table.issue_count, version: silver.data!.version, changes: table.transformations,
    })) ?? []),
    ...(gold.data?.tables.map(table => ({
      id: 'gold:' + table.name, layer: 'gold' as const, name: table.name, description: purpose[table.name] ?? '',
      rows: table.row_count, version: run.data!.run_id,
    })) ?? []),
  ];
  const indexed = new Map(tables.map(table => [table.id, table]));
  const bronzeMatches = !!bronze.data && bronze.data.snapshot_id === silver.data?.snapshot_id;
  const goldMatches = !!run.data && run.data.data_version === silver.data?.version && run.data.snapshot_id === silver.data?.snapshot_id;
  const mismatch = (bronze.data && silver.data && !bronzeMatches) || (run.data && silver.data && !goldMatches);
  const edges = tables.flatMap<Edge>(table => {
    const sources = table.layer === 'silver'
      ? tableCreation[table.name]?.inputs.map(name => 'silver:' + name) ??
        (bronzeMatches ? ['bronze:' + table.name + '.csv'] : [])
      : goldInputs[table.name]?.filter(id => goldMatches || !id.startsWith('silver:')) ?? [];
    return table.layer === 'bronze' ? [] : sources.filter(id => indexed.has(id)).map((id): Edge => [id, table.id]);
  });
  const goldTables = tables.filter(table => table.layer === 'gold');
  const requested = indexed.get(selected);
  const selection = requested && requested.layer !== 'bronze' ? requested : indexed.get(defaultTable) ?? goldTables[0] ?? tables.find(table => table.layer === 'silver');
  const related = new Set(selection ? [selection.id] : []);
  const inputs = new Set<string>();
  if (selection?.layer === 'silver') {
    // Derived Silver tables can be fed by other Silver tables. Show their originating Bronze files.
    for (const id of related) {
      for (const [from, to] of edges) {
        if (to !== id) continue;
        if (from.startsWith('bronze:')) inputs.add(from);
        else if (from.startsWith('silver:')) related.add(from);
      }
    }
  } else if (selection?.layer === 'gold') {
    for (const [from, to] of edges) {
      if (to === selection.id && from.startsWith('silver:')) inputs.add(from);
    }
  }
  const shownEdges = selection ? Array.from(inputs, (from): Edge => [from, selection.id]) : [];
  const visibleTables = tables.filter(table => table.id === selection?.id || inputs.has(table.id));
  const pending = bronze.isPending || silver.isPending || run.isPending || (!!run.data && gold.isPending);
  const errors = [
    { label: 'Bronze catalog', query: bronze },
    { label: 'Silver catalog', query: silver },
    { label: 'Gold run', query: run },
    { label: 'Gold catalog', query: gold },
    { label: 'Gold measure decisions', query: measures },
  ];

  function choose(id: string) {
    const table = indexed.get(id);
    if (!table) return;
    setSelected(id);
    window.history.replaceState(null, '', tableUrl(table));
  }

  return <div className="journey">
    <header className="journey-heading"><div><h1>Data journey</h1><p>Explore source files for Silver tables and direct Silver inputs for Gold.</p></div></header>
    <div className="journey-summary">
      {layers.map(name => {
        const items = tables.filter(table => table.layer === name);
        const ready = { bronze: bronze.data, silver: silver.data, gold: gold.data }[name];
        return <section key={name}><h2>{names[name]} {name === 'bronze' ? 'source files' : 'tables'}</h2>
          <strong>{ready ? formatCount(items.length) : '—'}</strong>
          {name === 'bronze' && bronze.data && <p>{items.filter(table => table.issues).length} sources with findings</p>}
          {name === 'silver' && silver.data && <p>{formatCount(silver.data.issues)} unresolved issues</p>}
          {name === 'gold' && measures.data && <p>{measures.data.filter(measure => measure.safety_status === 'blocked').length} blocked measures · {measures.data.filter(measure => measure.safety_status === 'human_review').length} need review</p>}
        </section>;
      })}
    </div>
    {pending && <p role="status">Loading published catalogs…</p>}
    {errors.filter(({ query }) => query.isError).map(({ label, query }) => <div key={label} className="error-panel" role="alert">
      <span>{label} unavailable.</span> <button onClick={() => void query.refetch()}>Retry {label}</button>
    </div>)}
    {mismatch && <div className="error-panel" role="alert">Published versions differ. Affected cross-layer links are unavailable.
      <button onClick={() => { void bronze.refetch(); void silver.refetch(); void run.refetch(); }}>Retry publication checks</button>
    </div>}
    <div className="journey-workspace">
      <section className="journey-catalog" aria-labelledby="journey-catalog-title">
        <h2 id="journey-catalog-title">Select a table</h2>
        {selectableLayers.map(name => {
          const items = tables.filter(table => table.layer === name);
          return <details key={name} className="journey-picker" open={selection?.layer === name ? true : undefined}>
            <summary>{names[name]} tables</summary>
            {items.length ? <ul className="journey-table-list" aria-label={names[name] + ' tables'}>
              {items.map(table => <li key={table.id}>
                <button type="button" aria-pressed={selection?.id === table.id} onClick={() => choose(table.id)}>
                  {table.name}
                </button>
              </li>)}
            </ul> : <p>{pending ? 'Loading tables…' : 'No tables available.'}</p>}
          </details>;
        })}
      </section>
      <section className="journey-canvas" aria-label="Table lineage">
        <header><h2>Table lineage</h2><span>Published snapshot</span></header>
        {selection ? <>
          <Lineage tables={visibleTables} edges={shownEdges} selection={selection} />
          <section className="journey-details" aria-label="Selected table">
            <h3>{selection.name}</h3>
            <p>{selection.description}</p>
            <dl><dt>Records</dt><dd>{formatCount(selection.rows)}</dd>
              <dt>{selection.layer === 'gold' ? 'Run' : 'Published version'}</dt><dd><code>{selection.version}</code></dd>
              {selection.issues !== undefined && <><dt>Quality</dt><dd>{formatCount(selection.issues)} {selection.layer === 'bronze' ? 'reported findings' : 'unresolved issues'}</dd></>}
            </dl>
            {selection.changes && Object.keys(selection.changes).length > 0 && <details><summary>Transformations</summary>
              <ul>{Object.entries(selection.changes).map(([label, value]) => <li key={label}>{label.replaceAll('_', ' ')} · {formatCount(value)}</li>)}</ul></details>}
            <a href={tableUrl(selection, true)}>{selection.layer === 'bronze' ? 'Inspect source' : 'Inspect table'}</a>
          </section>
        </> : <p>{pending ? 'Loading tables…' : 'No table is available to trace.'}</p>}
      </section>
    </div>
  </div>;
}
