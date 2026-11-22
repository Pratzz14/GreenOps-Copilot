import { useState } from 'react';
import { useGold } from './api/gold';
import DashboardPagination from './DashboardPagination';
import { RecommendationRow } from './DashboardRecommendations';
import DashboardRequest from './DashboardRequest';
import { carbonUnit, groupLabels, metricValue, monthLabel, sumAvailable, type GoldModels, type Group, type Metric, type Scenario } from './dashboardData';
import { groupSavings, labels, recommendationActions, spending, statuses, type RecommendationGroup } from './recommendationData';
import './dashboard.css';
import './recommendations.css';

type Run = GoldModels['GoldRun'];
type Status = keyof typeof statuses;
type Action = RecommendationGroup['action'];
const groups: Group[] = ['tool', 'department', 'provider', 'platform', 'location'];
const actionLabels: Record<Action, string> = { resize: 'Licences', shutdown: 'Servers', schedule: 'Data clusters' };
const metricOptions: [Metric, string][] = [['cost', 'Cost'], ['energy', 'Energy'], ['carbon', 'Emissions']];
const metricHeadings = { cost: 'Cost savings', energy: 'Energy savings', carbon: 'Location-based emissions savings' };
const metricPaths = {
  cost: 'M3 6h18v12H3z M3 10h18 M6 15h4',
  energy: 'M13.5 2 5 13h6l-.5 9L19 10h-6z',
  carbon: 'M20 3c0 10-1 15-8 15-4.2 0-7-2.6-7-6.4C5 6 11 6 15 5.1c2-.4 3.5-1.1 5-2.1ZM4 21c2-4.8 5.5-8.8 11-12',
};

function total(row: RecommendationGroup, metric: Metric) {
  const savings = groupSavings(row, metric, '');
  return sumAvailable(savings?.eligible, savings?.conditional);
}

function OverallSummary({ rows, basis }: { rows: RecommendationGroup[]; basis: string }) {
  const hasOmissions = rows.some(row => row.omitted_measure_count > 0);
  return <section className="recommendations-summary" aria-label="Overall summary">
    <h2>Potential annual savings</h2>
    <div className="recommendations-savings">
      {metricOptions.map(([metric]) => {
        const amount = rows.reduce<number | null>((sum, row) => sumAvailable(sum, total(row, metric)), null);
        const value = amount !== null && metric === 'cost' ? spending(amount) : metricValue(amount, metric, carbonUnit(basis));
        return <article className="recommendations-kpi" data-metric={metric} key={metric}>
          <header>
            <svg aria-hidden="true" className="recommendations-metric-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d={metricPaths[metric]} />
            </svg>
            <h3>{metricHeadings[metric]}</h3>
          </header>
          <p className="recommendations-kpi-value">{value}</p>
        </article>;
      })}
    </div>
    {hasOmissions && <p className="recommendations-omissions">Overlapping or shared estimates are excluded from the totals.</p>}
  </section>;
}

function ResultsTable({ rows, group, run, basis, metric }: {
  rows: RecommendationGroup[]; group: Group; run: string; basis: string; metric: Metric;
}) {
  const [page, setPage] = useState(0);
  const pageSize = 15;
  const currentPage = Math.min(page, Math.ceil(rows.length / pageSize) - 1);
  const offset = currentPage * pageSize;
  return <>
    <table className="dashboard-recommendations-table" aria-label="Recommendations for underused resources">
      <thead><tr><th scope="col">{groupLabels[group]} / recommended action</th><th scope="col">Underused resources</th>
        <th scope="col" aria-sort="descending">Annual savings <span aria-hidden="true">↓</span><small>{labels[metric]}</small></th>
        <th scope="col">Safety</th></tr></thead>
      <tbody>{rows.slice(offset, offset + pageSize).map(row =>
        <RecommendationRow key={row.id} row={row} run={run} basis={basis} metric={metric} selected={null} month="" scopeFirst />)}</tbody>
    </table>
    <DashboardPagination page={currentPage} total={rows.length} pageSize={pageSize} label="Recommendation pages" onPage={setPage} />
  </>;
}

function Published({ run }: { run: Run }) {
  const [scenario, setScenario] = useState<Scenario>('mid');
  const [group, setGroup] = useState<Group>('tool');
  const [metric, setMetric] = useState<Metric>('cost');
  const [search, setSearch] = useState('');
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const prefix = `/runs/${run.run_id}`;
  const overview = useGold<GoldModels['GoldOverview']>(`${prefix}/overview?scenario=${scenario}`);
  const query = useGold<RecommendationGroup[]>(`${prefix}/recommendation-groups?group=${group}&scenario=${scenario}`);
  const basis = overview.data?.emissions.unit ?? 'CO2';
  const term = search.trim().toLowerCase();
  const rows = query.data ?? [];
  const matches = rows.filter(row => (!action || row.action === action)
    && (!status || row.safety_counts[status as Status])
    && [row.scope, actionLabels[row.action], recommendationActions[row.action], ...row.members.map(member => member.resource)]
      .join(' ').toLowerCase().includes(term))
    .sort((a, b) => (total(b, metric) ?? -Infinity) - (total(a, metric) ?? -Infinity)
      || a.scope.localeCompare(b.scope) || a.id.localeCompare(b.id));
  const counts = { eligible: 0, human_review: 0, blocked: 0 };
  for (const row of matches) {
    for (const key of Object.keys(counts) as Status[]) counts[key] += row.safety_counts[key] ?? 0;
  }
  const resources = counts.eligible + counts.human_review + counts.blocked;
  function clearFilters() {
    setSearch('');
    setAction('');
    setStatus('');
  }

  return <section className="recommendations-page" aria-labelledby="recommendations-page-heading">
    <header className="recommendations-header">
      <div><h1 id="recommendations-page-heading">Recommendations</h1>
        <p>Usage baseline <span>·</span> {monthLabel(run.period_start)} – {monthLabel(run.period_end)}</p>
      </div>
      <fieldset className="recommendations-scenario">
        <legend>Savings assumptions</legend>
        <div>{(['low', 'mid', 'high'] as const).map(key =>
          <label key={key}><input type="radio" name="recommendations-scenario" value={key}
            checked={scenario === key} onChange={() => setScenario(key)} /><span>{key}</span></label>)}</div>
      </fieldset>
    </header>
    <DashboardRequest query={query} label="recommendations">{() =>
      <OverallSummary rows={matches} basis={basis} />}</DashboardRequest>
    <section className="dashboard-panel dashboard-data-panel recommendations-results" aria-labelledby="recommended-actions">
      <header className="recommendations-results-header">
        <div><h2 id="recommended-actions">Recommended actions</h2>
          {query.isSuccess && <span className="recommendations-match-count" aria-live="polite">{matches.length}<span className="dashboard-visually-hidden"> matching {matches.length === 1 ? 'recommendation' : 'recommendations'}</span></span>}
        </div>
        {query.isSuccess && <div className="recommendations-resource-status">
          <span>{resources} supporting {resources === 1 ? 'resource' : 'resources'}</span>
          <ul aria-label="Safety of supporting resources">
            <li data-status="eligible">{counts.eligible} eligible</li>
            <li data-status="human_review">{counts.human_review} need review</li>
            <li data-status="blocked">{counts.blocked} blocked</li>
          </ul>
        </div>}
      </header>
      <div className="recommendations-filters">
        <label className="recommendations-search">
          <span className="dashboard-visually-hidden">Find a recommendation</span>
          <svg aria-hidden="true" width="17" height="17" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
            <circle cx="8" cy="8" r="5.5" /><path d="m12.2 12.2 4.7 4.7" /></svg>
          <input type="search" placeholder="Search recommendations…" value={search} onChange={event => setSearch(event.target.value)} />
        </label>
        <button type="button" className="recommendations-filter-toggle" aria-expanded={filtersOpen} aria-controls="recommendations-filter-fields"
          onClick={() => setFiltersOpen(!filtersOpen)}>Filters{(action || status) && ' •'}</button>
        <div className="recommendations-filter-fields" id="recommendations-filter-fields" data-open={filtersOpen}>
          <label>Resource type
            <select value={action} onChange={event => setAction(event.target.value)}>
              <option value="">All types</option>
              {(Object.keys(actionLabels) as Action[]).filter(key => action === key || rows.some(row => row.action === key))
                .map(key => <option key={key} value={key}>{actionLabels[key]}</option>)}
            </select>
          </label>
          <label>Safety
            <select value={status} onChange={event => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              {(Object.keys(statuses) as Status[]).map(key => <option key={key} value={key}>{statuses[key]}</option>)}
            </select>
          </label>
          <label>Group by
            <select value={group} onChange={event => { setGroup(event.target.value as Group); clearFilters(); }}>
              {groups.map(key => <option key={key} value={key}>{groupLabels[key]}</option>)}
            </select>
          </label>
          <label>Savings shown
            <select value={metric} onChange={event => setMetric(event.target.value as Metric)}>
              {metricOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
        </div>
      </div>
      {query.isSuccess && (matches.length ? <ResultsTable key={JSON.stringify([scenario, group, metric, term, action, status])}
        rows={matches} group={group} run={run.run_id} basis={basis} metric={metric} /> :
        <div className="recommendations-empty"><p>{rows.length ? 'No recommendations match your filters.' : 'No recurring underuse was found in the published baseline.'}</p>
          {!!rows.length && <button type="button" onClick={clearFilters}>Clear filters</button>}</div>)}
    </section>
  </section>;
}

export default function Recommendations() {
  const current = useGold<Run>('/runs/current');
  return <div className="greenops-dashboard recommendations-workspace">
    <DashboardRequest query={current} label="published data">{run => <Published key={run.run_id} run={run} />}</DashboardRequest>
  </div>;
}
