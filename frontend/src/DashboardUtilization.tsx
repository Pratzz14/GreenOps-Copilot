import { useId, useState } from 'react';
import { useGold } from './api/gold';
import DashboardRequest from './DashboardRequest';
import DashboardPagination from './DashboardPagination';
import { metricLabels, metricValue, type CarbonUnit, type DashboardFilters, type Metric } from './dashboardData';

type Finding = {
  key: string;
  resource: string;
  category: string;
  observation: string;
  impact: Partial<Record<Metric, string>>;
  evidence: Record<string, number[]>;
};
type Scan = { items: Finding[]; assessed: number; insufficient: number };
const utilizationPageSize = 5;
const impactMetrics = ['cost', 'energy', 'carbon'] as const;

function ResourceRow({ row, metric, unit }: { row: Finding; metric: Metric; unit: CarbonUnit }) {
  const [expanded, setExpanded] = useState(false);
  const evidenceId = useId();

  return <>
    <tr className="dashboard-utilization-row" role="row">
      <th scope="row" role="rowheader">
        <button type="button" className="dashboard-utilization-resource" aria-expanded={expanded}
          aria-controls={evidenceId} onClick={() => setExpanded(open => !open)}>
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="m6 4 4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span><strong>{row.resource}</strong><small>{row.category}</small></span>
        </button>
      </th>
      <td className="dashboard-utilization-observation" role="cell">{row.observation.split('. ', 1)[0]}</td>
      {impactMetrics.map(impact => {
        const value = row.impact[impact] ?? null;
        return <td key={impact} role="cell" className="dashboard-utilization-impact" data-active={impact === metric}
          data-unavailable={value === null}>
          <span className="dashboard-utilization-mobile-label" aria-hidden="true">{metricLabels[impact]}</span>
          {metricValue(value, impact, unit)}
        </td>;
      })}
    </tr>
    <tr id={evidenceId} className="dashboard-utilization-evidence" role="row" hidden={!expanded}>
      <td colSpan={5} role="cell">
        <p>{row.observation}</p>
        <details><summary>Source rows</summary>
          <ul>{Object.entries(row.evidence).map(([file, numbers]) =>
            <li key={file}>{file} · {numbers.join(', ')}</li>)}</ul>
        </details>
      </td>
    </tr>
  </>;
}

function Results({ scan, matches, metric, unit }: { scan: Scan; matches: Finding[]; metric: Metric; unit: CarbonUnit }) {
  const [requestedPage, setPage] = useState(0);
  const rows = [...matches].sort((a, b) => Number(b.impact[metric] ?? -Infinity) - Number(a.impact[metric] ?? -Infinity)
    || a.resource.localeCompare(b.resource));
  const page = Math.min(requestedPage, Math.max(0, Math.ceil(rows.length / utilizationPageSize) - 1));
  const start = page * utilizationPageSize;

  if (!rows.length) return <p className="dashboard-utilization-empty">{scan.items.length ? 'No resources match your search.' :
    scan.assessed ? 'No underused resources matched the selected filters.' :
      'No resources could be assessed with the selected filters.'}</p>;

  return <>
    <table className="dashboard-utilization-table" role="table" aria-label="Resource utilization and impact">
      <thead role="rowgroup">
        <tr role="row">
          <th scope="col" role="columnheader">Resource</th>
          <th scope="col" role="columnheader">Observation</th>
          {impactMetrics.map(impact => <th key={impact} scope="col" role="columnheader"
            className="dashboard-utilization-impact" aria-sort={impact === metric ? 'descending' : undefined}>
            {metricLabels[impact]}{impact === metric && <svg aria-hidden="true" width="16" height="16"
              viewBox="0 0 16 16" fill="none">
              <path d="M8 3v10m-4-4 4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>}
          </th>)}
        </tr>
      </thead>
      <tbody role="rowgroup">
        {rows.slice(start, start + utilizationPageSize).map(row =>
          <ResourceRow key={row.key} row={row} metric={metric} unit={unit} />)}
      </tbody>
    </table>
    <DashboardPagination page={page} total={rows.length} label="Resource pages" onPage={setPage} pageSize={utilizationPageSize} />
  </>;
}

export default function DashboardUtilization({ run, filters, unit, onMetric }: {
  run: string; filters: DashboardFilters; unit: CarbonUnit; onMetric: (metric: Metric) => void;
}) {
  const [search, setSearch] = useState('');
  const params = new URLSearchParams({
    scenario: filters.scenario, group: filters.group, driver: filters.driver, include_estimates: 'true',
  });
  filters.period?.forEach(month => params.append('months', month.slice(0, 7)));
  const query = useGold<Scan>(`/runs/${run}/utilization?${params}`);
  const searchTerm = search.trim().toLowerCase();
  const scan = query.isError ? undefined : query.data;
  const matches = scan?.items.filter(row => `${row.resource} ${row.category}`.toLowerCase().includes(searchTerm)) ?? [];

  return <section className="dashboard-panel dashboard-utilization" aria-labelledby="dashboard-utilization">
    <div className="dashboard-utilization-header">
      <div><h2 id="dashboard-utilization">Utilization analysis</h2>
        <p>{filters.driver || 'All drivers'} · {filters.period ? `${filters.period.length} months selected` : 'Baseline period'}</p>
        {scan && <p className="dashboard-utilization-count">{matches.length} matches · {scan.assessed} assessed · {scan.insufficient} with insufficient observations</p>}
      </div>
      <div className="dashboard-utilization-controls">
        <label>Find a resource<input type="search" value={search} onChange={event => setSearch(event.target.value)} /></label>
        <label>Sort resources by
          <select value={filters.metric} onChange={event => onMetric(event.target.value as Metric)}>
            <option value="cost">Spending · highest first</option>
            <option value="energy">Energy · highest first</option>
            <option value="carbon">CO₂e · highest first</option>
          </select>
        </label>
      </div>
    </div>
    <DashboardRequest query={query} label="utilization analysis">{data =>
      <Results key={JSON.stringify([params.toString(), filters.metric, searchTerm])}
        scan={data} matches={matches} metric={filters.metric} unit={unit} />}
    </DashboardRequest>
  </section>;
}
