import { useState } from 'react';
import DashboardInfo from './DashboardInfo';
import { useGold } from './api/gold';
import DashboardCharts from './DashboardCharts';
import DashboardUtilization from './DashboardUtilization';
import DashboardRecommendations from './DashboardRecommendations';
import type { RecommendationGroup } from './recommendationData';
import DashboardRequest from './DashboardRequest';
import DashboardChat from './DashboardChat';
import { CalculationFactors, Evidence } from './GoldEvidence';
import {
  baselineMonths, coverageLabels, emissionsUnit, dashboardDefaults, groupLabels, metricLabels, metricValue, monthLabel, number,
  sumAvailable, type Breakdown, type DashboardFilters, type GoldModels, type Group, type Metric, type Scenario,
} from './dashboardData';
import { chfFormat } from './numberFormat';
import './dashboard.css';

type Run = GoldModels['GoldRun'];
type Overview = GoldModels['GoldOverview'];

function PeriodPicker({ months, period, onChange }: {
  months: string[];
  period: DashboardFilters['period'];
  onChange: (period: DashboardFilters['period']) => void;
}) {
  const selected = period ?? months;
  return <div className="dashboard-filter">
    <span id="dashboard-period-label">Period</span>
    <details className="dashboard-period" onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false;
    }} onKeyDown={event => {
      if (event.key !== 'Escape' || !event.currentTarget.open) return;
      event.currentTarget.querySelector('summary')?.focus();
      event.currentTarget.open = false;
    }}>
      <summary aria-labelledby="dashboard-period-label dashboard-period-selection">
        <span id="dashboard-period-selection">{period === null ? 'All months' :
          selected.length === 1 ? monthLabel(selected[0]) : `${selected.length} months selected`}</span>
      </summary>
      <fieldset className="dashboard-period-options" aria-labelledby="dashboard-period-label">
        <label><input type="checkbox" checked={period === null}
          onChange={event => onChange(event.target.checked ? null : [])} />All months</label>
        {months.map(month => <label key={month}><input type="checkbox" checked={selected.includes(month)}
          onChange={event => {
            const checked = event.target.checked;
            const next = months.filter(candidate => candidate === month ? checked : selected.includes(candidate));
            onChange(next.length === months.length ? null : next);
          }} />{monthLabel(month)}</label>)}
      </fieldset>
    </details>
  </div>;
}

function Filters({ filters, months, update }: {
  filters: DashboardFilters;
  months: string[];
  update: (filters: DashboardFilters) => void;
}) {
  return <section className="dashboard-filters dashboard-panel" aria-label="Dashboard filters">
    <div className="dashboard-filter">
      <label htmlFor="dashboard-scenario">Assumptions</label>
      <select id="dashboard-scenario" value={filters.scenario} onChange={event => update({ ...filters, scenario: event.target.value as Scenario })}>
        <option value="low">Low</option><option value="mid">Mid</option><option value="high">High</option>
      </select>
    </div>
    <div className="dashboard-filter">
      <label htmlFor="dashboard-group">Group by</label>
      <select id="dashboard-group" value={filters.group} onChange={event => update({ ...filters, group: event.target.value as Group, driver: '' })}>
        {Object.entries(groupLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
    </div>
    <div className="dashboard-filter">
      <label htmlFor="dashboard-metric">Metric</label>
      <select id="dashboard-metric" value={filters.metric} onChange={event => update({ ...filters, metric: event.target.value as Metric })}>
        {Object.entries(metricLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
    </div>
    <PeriodPicker months={months} period={filters.period} onChange={period => update({ ...filters, period })} />
    <button className="dashboard-text-button dashboard-reset" type="button" onClick={() => update(dashboardDefaults)}>Reset filters</button>
  </section>;
}

function Footprint({ overview, run }: { overview: Overview; run: Run }) {
  const unit = emissionsUnit(overview);
  const emissions = overview.reporting_kg_co2e ?? null;
  const spending = sumAvailable(overview.cost.value, overview.imputed_cost_chf);
  const metrics = [
    ['carbon', 'Estimated emissions', metricValue(emissions, 'carbon', unit), overview.reporting_carbon_coverage],
    ['energy', 'Estimated electricity use', metricValue(overview.energy.value, 'energy', unit), overview.energy_coverage],
    ['cost', 'Estimated spending', spending === null ? 'Unavailable' : chfFormat.format(spending),
      overview.cost_coverage],
  ] as const;
  return <dl className="dashboard-kpis">
      {metrics.map(([metric, label, value, coverage]) => <div key={metric} data-metric={metric}>
        <dt>
          <span>{label}</span>
          <DashboardInfo label={label}>
            <p>{metric === 'cost' ? 'Recorded charges plus missing usage charges estimated from comparable unit prices.'
              : metric === 'energy' ? 'Usage × matching energy intensity × PUE for IT-side estimates.'
                : 'Facility electricity × location-based grid factors.'}</p>
            {metric === 'carbon' && <p>The submission estimates location-based operating emissions, including the Swiss CO₂e proxy.</p>}
            <p>{metric === 'cost' ? value : `${value} · ${coverageLabels[coverage]}`}</p>
            <Evidence run={run.run_id} id={overview.evidence_set_id} label="Sources and coverage" />
            {metric === 'cost' ? <>
              <p>CHF uses a factor of 1. EUR and USD use the rate for the billing month.</p>
              <p>Recorded spending {overview.cost.value === null ? 'unavailable' : chfFormat.format(Number(overview.cost.value))}</p>
              <details className="gold-evidence">
                <summary>Billing coverage details</summary>
                <p>{number.format(overview.included_rows)} recorded charges · {number.format(overview.missing_amount_rows)} missing source amounts
                  {' · '}{number.format(overview.missing_fx_rows)} missing exchange rates · {number.format(overview.review_rows)} charges under review</p>
                {overview.recovered_cost_chf != null && <p>Recorded spending includes {metricValue(overview.recovered_cost_chf, 'cost', unit)} recovered from exact billing mirrors.</p>}
              </details>
            </> : <CalculationFactors run={run.run_id} ids={metric === 'energy'
              ? ['vcpu', 'database_vcore', 'build_runner', 'node', 'gpu', 'storage', 'tokens', 'message', 'pue']
              : ['grid_de', 'grid_ie', 'grid_ch_operating']} />}
          </DashboardInfo>
        </dt>
        <dd>{value}</dd>
        {metric !== 'cost' && <dd><span className={`dashboard-coverage dashboard-coverage-${coverage}`}>{coverageLabels[coverage]}</span></dd>}
      </div>)}
  </dl>;
}

function PublishedDashboard({ run }: { run: Run }) {
  const [filters, setFilters] = useState(dashboardDefaults);
  const [driverEvidence, setDriverEvidence] = useState<string[]>();
  const [selection, setSelection] = useState<{ id: string; click: number } | null>(null);
  const { scenario, group } = filters;
  const months = baselineMonths(run.period_start, run.period_end);
  const prefix = `/runs/${run.run_id}`;
  const overview = useGold<Overview>(`${prefix}/overview?scenario=${scenario}`);
  const breakdown = useGold<Breakdown[]>(`${prefix}/breakdowns?group=${group}&scenario=${scenario}`);
  const params = new URLSearchParams({ scenario, group, driver: filters.driver });
  filters.period?.forEach(month => params.append('months', month.slice(0, 7)));
  const emptyPeriod = filters.period?.length === 0;
  const recommendations = useGold<RecommendationGroup[]>(`${prefix}/recommendation-groups?${params}`, !emptyPeriod);
  const recommendationLinks = new Map(recommendations.data?.flatMap(row => row.members.map(member => [member.finding_key, member.id])));

  function updateFilters(next: DashboardFilters) {
    setDriverEvidence(undefined);
    setFilters(next);
  }

  return <>
    <Filters filters={filters} months={months} update={updateFilters} />
    <section className="dashboard-panel dashboard-footprint" aria-label="Company-wide baseline footprint">
      <DashboardRequest query={overview} label="baseline footprint">{data => <Footprint run={run} overview={data} />}</DashboardRequest>
    </section>
    <div className="dashboard-charts">
      <DashboardCharts query={breakdown} months={months} filters={filters} unit={emissionsUnit(overview.data)}
        driverEvidence={driverEvidence} onDriver={driver => updateFilters({ ...filters, driver })} />
    </div>
    <DashboardUtilization run={run.run_id} filters={filters} unit={emissionsUnit(overview.data)}
      recommendationLinks={recommendationLinks} onRecommendation={id =>
        setSelection(previous => ({ id, click: (previous?.click ?? 0) + 1 }))}
      onMetric={metric => updateFilters({ ...filters, metric })} />
    <DashboardRecommendations query={recommendations} run={run.run_id} basis={overview.data?.emissions.unit ?? 'CO2'}
      metric={filters.metric} group={group} emptyPeriod={emptyPeriod} selection={selection} filterKey={params.toString()} />
    <DashboardChat run={run.run_id} filters={filters} onShowDrivers={(scope, labels) => {
      if (scope.group === 'subject') return;
      setFilters({
        scenario: scope.scenario, group: scope.group, metric: scope.metric, driver: scope.driver ?? '',
        period: scope.months?.map(month => month + '-01') ?? null,
      });
      setDriverEvidence(labels);
    }} />
  </>;
}

export default function Dashboard() {
  const current = useGold<Run>('/runs/current');
  return <div className="greenops-dashboard">
    <h1 className="dashboard-visually-hidden">Dashboard</h1>
    <DashboardRequest query={current} label="published data">{run => <PublishedDashboard key={run.run_id} run={run} />}</DashboardRequest>
  </div>;
}
