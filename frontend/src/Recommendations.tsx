import { useState } from 'react';
import { useGold } from './api/gold';
import DashboardRequest from './DashboardRequest';
import { RecommendationRow } from './DashboardRecommendations';
import { carbonUnit, groupLabels, metricValue, sumAvailable, type GoldModels, type Group, type Metric, type Scenario } from './dashboardData';
import { groupSavings, labels, spending, statuses, type RecommendationGroup } from './recommendationData';
import './dashboard.css';

type Run = GoldModels['GoldRun'];
type Status = keyof typeof statuses;
type Action = RecommendationGroup['action'];
const groups: Group[] = ['tool', 'department', 'provider', 'platform', 'location'];
const actionLabels: Record<Action, string> = { resize: 'Licences', shutdown: 'Servers', schedule: 'Data clusters' };
const metricOptions: [Metric, string][] = [['cost', 'Cost'], ['energy', 'Energy'], ['carbon', 'Emissions']];

function total(row: RecommendationGroup, metric: Metric) {
  const savings = groupSavings(row, metric, '');
  return sumAvailable(savings?.eligible, savings?.conditional);
}

function OverallSummary({ rows, basis }: { rows: RecommendationGroup[]; basis: string }) {
  const counts = { eligible: 0, human_review: 0, blocked: 0 };
  for (const row of rows) {
    for (const status of Object.keys(counts) as Status[]) counts[status] += row.safety_counts[status] ?? 0;
  }
  const resources = counts.eligible + counts.human_review + counts.blocked;
  const hasOmissions = rows.some(row => row.omitted_measure_count > 0);

  return <section aria-labelledby="overall-recommendations-heading" className="recommendations-summary">
    <h2 id="overall-recommendations-heading">Overall summary</h2>
    <dl aria-live="polite">
      <div><dt>Matching recommendations</dt><dd>{rows.length}</dd></div>
      <div><dt>Supporting resources</dt><dd>{resources}</dd>
        <dd><small>{counts.eligible} eligible · {counts.human_review} need review · {counts.blocked} blocked</small></dd>
      </div>
      {metricOptions.map(([metric]) => {
        let eligible: number | null = null;
        let conditional: number | null = null;
        let quantified = 0;
        for (const row of rows) {
          const savings = groupSavings(row, metric, '');
          eligible = sumAvailable(eligible, savings?.eligible);
          conditional = sumAvailable(conditional, savings?.conditional);
          quantified += savings?.quantified ?? 0;
        }
        const total = sumAvailable(eligible, conditional);
        if (metric !== 'cost' && total === null) return null;
        const format = (value: number) => metric === 'cost' ? spending(value) : metricValue(value, metric, carbonUnit(basis));
        const partial = quantified > 0 && (hasOmissions || quantified < resources - counts.blocked);
        return <div key={metric}>
          <dt>{metric === 'cost' ? 'Potential annual CHF savings' : `Annual ${labels[metric].toLowerCase()} savings`}</dt>
          <dd>{total === null ? 'Unavailable' : format(total)}</dd>
          {total !== null && <dd><small>
            Eligible {eligible === null ? 'unavailable' : format(eligible)} · Conditional {conditional === null ? 'unavailable' : format(conditional)}
          </small></dd>}
          {partial && <dd><small>Partial coverage</small></dd>}
        </div>;
      })}
    </dl>
    {hasOmissions && <p>Overlapping or shared estimates are excluded from the totals.</p>}
  </section>;
}

function List({ rows, group, run, basis, metric }: {
  rows: RecommendationGroup[]; group: Group; run: string; basis: string; metric: Metric;
}) {
  const [search, setSearch] = useState('');
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');
  const term = search.trim().toLowerCase();
  const matches = rows.filter(row => (!action || row.action === action)
    && (!status || row.safety_counts[status as Status])
    && [row.scope, actionLabels[row.action], ...row.members.map(member => member.resource)].join(' ').toLowerCase().includes(term))
    .sort((a, b) => (total(b, metric) ?? -Infinity) - (total(a, metric) ?? -Infinity)
      || a.scope.localeCompare(b.scope) || a.id.localeCompare(b.id));
  const present = (key: Action) => rows.some(row => row.action === key);

  return <>
    <div className="recommendations-filters">
      <label>Find a recommendation
        <input type="search" value={search} onChange={event => setSearch(event.target.value)} />
      </label>
      <label>Resource type
        <select value={action} onChange={event => setAction(event.target.value)}>
          <option value="">All types</option>
          {(Object.keys(actionLabels) as Action[]).filter(present).map(key => <option key={key} value={key}>{actionLabels[key]}</option>)}
        </select>
      </label>
      <label>Safety
        <select value={status} onChange={event => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          {(Object.keys(statuses) as Status[]).map(key => <option key={key} value={key}>{statuses[key]}</option>)}
        </select>
      </label>
    </div>
    <OverallSummary rows={matches} basis={basis} />
    {matches.length ? <table className="dashboard-recommendations-table" aria-label="Recommendations for underused resources">
      <thead><tr><th scope="col">Recommended action<small>{groupLabels[group]}</small></th><th scope="col">Underused resources</th>
        <th scope="col" aria-sort="descending">Potential annual savings<small>{labels[metric]}</small></th>
        <th scope="col">Safety</th></tr></thead>
      <tbody>{matches.map(row =>
        <RecommendationRow key={row.id} row={row} run={run} basis={basis} metric={metric} selected={null} month="" />)}</tbody>
    </table> : <p>{rows.length ? 'No recommendations match your filters.' : 'No recurring underuse was found in the published baseline.'}</p>}
  </>;
}

function Published({ run }: { run: Run }) {
  const [scenario, setScenario] = useState<Scenario>('mid');
  const [group, setGroup] = useState<Group>('tool');
  const [metric, setMetric] = useState<Metric>('cost');
  const prefix = `/runs/${run.run_id}`;
  const overview = useGold<GoldModels['GoldOverview']>(`${prefix}/overview?scenario=${scenario}`);
  const query = useGold<RecommendationGroup[]>(`${prefix}/recommendation-groups?group=${group}&scenario=${scenario}`);

  return <section className="dashboard-panel dashboard-recommendations" aria-labelledby="recommendations-page-heading">
    <div className="recommendations-header">
      <div>
        <h1 id="recommendations-page-heading">Recommendations</h1>
        <p>Underused resources merged into one recommendation per {groupLabels[group].toLowerCase()} and action.</p>
      </div>
      <div className="recommendations-controls">
        <label>Merge by
          <select value={group} onChange={event => setGroup(event.target.value as Group)}>
            {groups.map(key => <option key={key} value={key}>{groupLabels[key]}</option>)}
          </select>
        </label>
        <label>Savings shown
          <select value={metric} onChange={event => setMetric(event.target.value as Metric)}>
            {metricOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </label>
        <label>Assumptions
          <select value={scenario} onChange={event => setScenario(event.target.value as Scenario)}>
            <option value="low">Low</option><option value="mid">Mid</option><option value="high">High</option>
          </select>
        </label>
      </div>
    </div>
    <DashboardRequest query={query} label="recommendations">{data =>
      <List key={group} rows={data} group={group} run={run.run_id} basis={overview.data?.emissions.unit ?? 'CO2'} metric={metric} />}</DashboardRequest>
  </section>;
}

export default function Recommendations() {
  const current = useGold<Run>('/runs/current');
  return <div className="greenops-dashboard">
    <DashboardRequest query={current} label="published data">{run => <Published key={run.run_id} run={run} />}</DashboardRequest>
  </div>;
}
