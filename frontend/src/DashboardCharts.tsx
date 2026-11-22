import { useEffect, useRef, useState } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import DashboardRequest from './DashboardRequest';
import DashboardPagination, { dashboardPageSize } from './DashboardPagination';
import {
  coverageLabels, groupLabels, metricLabels, metricUnit, metricValue, monthLabel,
  number, periodBreakdown, rowCoverage, rowValue, trendPoints,
  type Breakdown, type CarbonUnit, type DashboardFilters, type Metric,
} from './dashboardData';

function MonthlyTrend({ rows, months, filters, unit }: {
  rows: Breakdown[];
  months: string[];
  filters: DashboardFilters;
  unit: CarbonUnit;
}) {
  const { driver, metric } = filters;
  const points = trendPoints(rows, months, metric, driver);
  const plot = points.map(point => ({
    ...point,
    plotValue: point.value === null ? null : metric === 'carbon' ? point.value / 1000 : point.value,
  }));
  const hasValues = plot.some(point => point.plotValue !== null);
  return <>
    {hasValues ? <div className="dashboard-trend" role="img" aria-label={`Monthly ${metricLabels[metric]} for ${driver || 'the company'}`}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={plot} margin={{ top: 12, right: 25, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#e2e9e1" />
          <XAxis dataKey="month" minTickGap={8} tickFormatter={month => monthLabel(month, false)}
            tickLine={false} tick={{ fontSize: 11, fill: '#435a4d' }} stroke="#bdcbbf" />
          <YAxis domain={['auto', 'auto']} width={62} tickLine={false} stroke="#bdcbbf"
            tick={{ fontSize: 11, fill: '#435a4d' }} tickFormatter={value => number.format(Number(value))} />
          <Tooltip labelFormatter={month => monthLabel(String(month))}
            formatter={value => [metricValue(Number(value) * (metric === 'carbon' ? 1000 : 1), metric, unit), metricLabels[metric]]} />
          <Area type="linear" dataKey="plotValue" fill="#e3efe0" fillOpacity={0.7} baseValue="dataMin"
            stroke="#315e46" strokeWidth={2.4}
            dot={{ r: 2.6, fill: '#fff', strokeWidth: 2 }} activeDot={{ r: 4 }}
            connectNulls={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div> : <p className="dashboard-request">No published monthly values for this selection.</p>}
    <details className="dashboard-disclosure">
      <summary>View monthly data</summary>
      <div className="table-scroll dashboard-table-scroll" tabIndex={0} aria-label="Monthly footprint data">
        <table className="dashboard-table">
          <thead><tr><th scope="col">Month</th><th scope="col">{metricUnit(metric, unit)}</th><th scope="col">Coverage</th></tr></thead>
          <tbody>{points.map(point => <tr key={point.month}>
            <th scope="row">{monthLabel(point.month)}</th>
            <td>{metricValue(point.value, metric, unit)}</td>
            <td>{point.value === null ? 'Unknown' : point.partial ? 'Partial' : 'Available'}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </details>
  </>;
}

const energyPlanningNotes: Record<string, string> = {
  'm365:storage-gb-days': 'Storage only · partial coverage',
  'azure_costs:capacity-day': 'Planning estimate · capacity assumed',
  'aws_costs:gb': 'Planning estimate · transmission only',
  'hoster_invoice:gb': 'Planning estimate · transmission only',
};

function MetricCells({ row, unit }: { row: Breakdown; unit: CarbonUnit }) {
  return (['carbon', 'energy', 'cost'] as Metric[]).map(metric => {
    const baseline = rowValue(row, metric);
    const planning = metric === 'energy' ? row.planning_kwh : metric === 'carbon' ? row.planning_kg_co2e : null;
    if (baseline === null && planning != null) {
      const notes = new Set((row.planning_energy_boundaries ?? []).map(boundary => energyPlanningNotes[boundary]));
      const note = metric === 'energy' && notes.size === 1 ? [...notes][0] :
        metric === 'carbon' && row.planning_kwh == null ? 'Regional planning estimate' : undefined;
      const display = metric === 'carbon' && Math.abs(Number(planning)) < 1000
        ? `${number.format(Number(planning))} kg CO₂e` : metricValue(planning, metric, unit);
      return <td key={metric}>{display}<small>{note ?? 'Planning estimate'}</small></td>;
    }
    if (baseline === null && metric === 'energy') {
      return <td key={metric}>{row.needs_energy_factor ? 'Service energy factor needed' : 'Usage data needed'}</td>;
    }
    if (baseline === null && metric === 'carbon') {
      const hasEnergy = row.estimated_kwh !== null || row.planning_kwh != null;
      return <td key={metric}>{hasEnergy ? 'Hosting or grid factor needed' : 'Electricity estimate needed'}</td>;
    }
    return <td key={metric}>{metricValue(baseline, metric, unit)}
      <small>{coverageLabels[rowCoverage(row, metric)]}</small>
    </td>;
  });
}

function Drivers({ rows, filters, unit, evidence, selectDriver }: {
  rows: Breakdown[];
  filters: DashboardFilters;
  unit: CarbonUnit;
  evidence?: string[];
  selectDriver: (driver: string) => void;
}) {
  const { driver, group, metric, period, scenario } = filters;
  const filterKey = JSON.stringify([scenario, group, metric, period]);
  const sorted = periodBreakdown(rows, period)
    .map(row => ({ row, value: rowValue(row, metric) }))
    .sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity) || a.row.driver.localeCompare(b.row.driver));
  const target = sorted.findIndex(({ row, value }) => value !== null && evidence?.includes(row.driver));
  const [pagination, setPagination] = useState({ filterKey, evidence, page: 0 });
  const pageChanged = pagination.filterKey !== filterKey || pagination.evidence !== evidence;
  const requestedPage = pageChanged || (evidence && pagination.page === -1)
    ? Math.floor(Math.max(0, target) / dashboardPageSize) : pagination.page;
  if (pageChanged) setPagination({ filterKey, evidence, page: evidence ? -1 : 0 });
  const page = Math.min(requestedPage, Math.max(0, Math.ceil(sorted.length / dashboardPageSize) - 1));
  const start = page * dashboardPageSize;
  const visible = sorted.slice(start, start + dashboardPageSize);
  const ranked = visible.flatMap(({ row, value }) => value === null ? [] : [{ row, value }]);
  const max = Math.max(0, ...sorted.map(entry => entry.value ?? 0));
  const min = Math.min(0, ...sorted.map(entry => entry.value ?? 0));
  const scale = max - min || 1;
  const evidenceButton = useRef<HTMLButtonElement>(null);
  const focusedEvidence = useRef<string[]>(undefined);
  useEffect(() => {
    const button = evidenceButton.current;
    if (evidence && button && focusedEvidence.current !== evidence) {
      focusedEvidence.current = evidence;
      button.focus({ preventScroll: true });
      button.scrollIntoView({ block: 'center' });
    }
  }, [evidence, target, page]);

  return <>
    {ranked.length ? (
      <ul className="dashboard-bars" aria-label={`Ranked ${groupLabels[group].toLowerCase()} drivers`}>
        {ranked.map(({ row, value }) => {
          const partial = rowCoverage(row, metric) === 'partial';
          return <li key={row.driver}>
            <button type="button" aria-pressed={driver === row.driver} onClick={() => selectDriver(row.driver)}
              data-chat-evidence={evidence?.includes(row.driver) || undefined}
              ref={sorted[target]?.row.driver === row.driver ? evidenceButton : undefined}>
              <span className="dashboard-bar-name">{row.driver}{partial && <span className="dashboard-coverage-dot" title="Partial coverage" />}</span>
              <span className="dashboard-bar-track" aria-hidden="true">
                <span style={{ left: `${(Math.min(0, value) - min) / scale * 100}%`, width: `${Math.abs(value) / scale * 100}%` }} />
              </span>
              <span className="dashboard-bar-value">{metricValue(value, metric, unit)}{partial && <span className="dashboard-visually-hidden">, partial coverage</span>}</span>
            </button>
          </li>;
        })}
      </ul>
    ) : <p className="dashboard-request">{page ? 'No published driver values on this page.' :
      'No published driver values for this selection.'}</p>}
    <DashboardPagination page={page} total={sorted.length} label="Driver pages"
      onPage={next => setPagination({ filterKey, evidence, page: next })} />
    <details className="dashboard-disclosure">
      <summary>View breakdown</summary>
      {!sorted.length ? <p>No records for this period.</p> :
        <div className="table-scroll dashboard-table-scroll" tabIndex={0} aria-label="Full footprint breakdown">
          <table className="dashboard-table">
            <thead><tr><th scope="col">{groupLabels[group]}</th><th scope="col">Estimated emissions</th><th scope="col">Energy</th>
              <th scope="col">Estimated spending</th><th scope="col">Imputed spending</th></tr></thead>
            <tbody>{visible.map(({ row }) => <tr key={row.driver}>
              <th scope="row"><button type="button" className="dashboard-text-button" aria-pressed={driver === row.driver}
                onClick={() => selectDriver(row.driver)}>{row.driver}</button></th>
              <MetricCells row={row} unit={unit} />
              <td>{row.imputed_cost_chf == null ? '—' : metricValue(row.imputed_cost_chf, 'cost', unit)}
                {row.recovered_cost_chf != null &&
                  <small>Recorded includes {metricValue(row.recovered_cost_chf, 'cost', unit)} recovered</small>}
              </td>
            </tr>)}</tbody>
          </table>
        </div>}
    </details>
  </>;
}

export default function DashboardCharts({ query, months, filters, unit, driverEvidence, onDriver }: {
  query: UseQueryResult<Breakdown[], Error>;
  months: string[];
  filters: DashboardFilters;
  unit: CarbonUnit;
  driverEvidence?: string[];
  onDriver: (driver: string) => void;
}) {
  const selected = filters.period ?? months;
  const periodLabel = filters.period === null ? 'Baseline year' :
    selected.length === 1 ? monthLabel(selected[0]) : `${selected.length} months selected`;
  return <>
    <section className="dashboard-panel dashboard-chart-panel" aria-labelledby="dashboard-trend">
      <h2 id="dashboard-trend">Monthly footprint</h2>
      <div className="dashboard-chart-meta">
        <span>{metricUnit(filters.metric, unit)} · {filters.driver || 'All drivers'}</span>
        {filters.driver && <button className="dashboard-text-button" type="button" onClick={() => onDriver('')}>Clear driver</button>}
      </div>
      {filters.period !== null && <p className="dashboard-selected-month">{periodLabel}</p>}
      <DashboardRequest query={query} label="monthly data">
        {rows => <MonthlyTrend rows={rows} months={selected} filters={filters} unit={unit} />}
      </DashboardRequest>
    </section>
    <section className="dashboard-panel dashboard-chart-panel" aria-labelledby="dashboard-drivers">
      <h2 id="dashboard-drivers">Biggest drivers</h2>
      <p className="dashboard-chart-meta">{metricUnit(filters.metric, unit)} · {periodLabel}</p>
      <DashboardRequest query={query} label="driver data">
        {rows => <Drivers rows={rows} filters={filters} unit={unit} evidence={driverEvidence}
          selectDriver={name => onDriver(name === filters.driver ? '' : name)} />}
      </DashboardRequest>
    </section>
  </>;
}
