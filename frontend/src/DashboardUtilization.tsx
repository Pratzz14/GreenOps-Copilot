import { useState } from 'react';
import { useGold } from './api/gold';
import DashboardRequest from './DashboardRequest';
import DashboardPagination from './DashboardPagination';
import { metricLabels, metricValue, type CarbonUnit, type DashboardFilters, type Metric } from './dashboardData';

type Finding = {
  key: string;
  resource: string;
  category: string;
  observation: string;
  action: string;
  impact: Partial<Record<Metric, string>>;
  evidence: Record<string, number[]>;
};
type Scan = { items: Finding[]; assessed: number; insufficient: number };
const utilizationPageSize = 5;

function Results({ scan, search, metric, unit }: { scan: Scan; search: string; metric: Metric; unit: CarbonUnit }) {
  const [requestedPage, setPage] = useState(0);
  const rows = scan.items
    .filter(row => `${row.resource} ${row.category} ${row.action}`.toLowerCase().includes(search))
    .sort((a, b) => Number(b.impact[metric] ?? -Infinity) - Number(a.impact[metric] ?? -Infinity)
      || a.resource.localeCompare(b.resource));
  const page = Math.min(requestedPage, Math.max(0, Math.ceil(rows.length / utilizationPageSize) - 1));
  const start = page * utilizationPageSize;

  return <>
    <p>Impact shown for the selected period.</p>
    <p>{rows.length} matches · {scan.assessed} assessed · {scan.insufficient} with insufficient observations</p>
    {rows.length === 0 && <p>{search && scan.items.length ? 'No resources match your search.' :
      scan.assessed ? 'No underused resources matched the selected filters.' :
        'No resources could be assessed with the selected filters.'}</p>}
    {rows.slice(start, start + utilizationPageSize).map(row => <details key={row.key} className="dashboard-utilization-row">
      <summary><span><strong>{row.resource}</strong><small>{row.category}</small><small>{row.observation.split('. ', 1)[0]}</small></span>
        <span>{row.action}</span>
        <span className="utilization-impact">
          {(['cost', 'energy', 'carbon'] as const).map(impact => <span key={impact}>
            <small>{metricLabels[impact]}</small>
            {metricValue(row.impact[impact] ?? null, impact, unit)}
          </span>)}
        </span></summary>
      <div className="dashboard-utilization-evidence">
        <p>{row.observation}</p>
        <details><summary>Source rows</summary>
          <ul>{Object.entries(row.evidence).map(([file, numbers]) =>
            <li key={file}>{file} · {numbers.join(', ')}</li>)}</ul>
        </details>
      </div>
    </details>)}
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

  return <section className="dashboard-panel" aria-labelledby="dashboard-utilization">
    <div className="dashboard-utilization-header">
      <div><h2 id="dashboard-utilization">Utilization analysis</h2>
        <p>{filters.driver || 'All drivers'} · {filters.period ? `${filters.period.length} months selected` : 'Baseline period'}</p>
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
    <DashboardRequest query={query} label="utilization analysis">{scan =>
      <Results key={JSON.stringify([params.toString(), filters.metric, searchTerm])}
        scan={scan} search={searchTerm} metric={filters.metric} unit={unit} />}
    </DashboardRequest>
  </section>;
}
