import { useState } from 'react';
import { useGold } from './api/gold';
import DashboardRequest from './DashboardRequest';
import { Evidence } from './GoldEvidence';
import { metricValue, number, type GoldModels, type Scenario } from './dashboardData';

type Row = GoldModels['GoldCoverageRow'];

const stateLabels: Record<Row['state'], string> = {
  estimated: 'Estimated',
  partial_activity: 'Partial activity',
  missing_activity: 'Missing activity',
  missing_energy_factor: 'Service energy factor needed',
  missing_grid_factor: 'Hosting or grid factor needed',
};

function Estimate({ value, planning, metric }: {
  value: string | null | undefined;
  planning: string | null | undefined;
  metric: 'energy' | 'carbon';
}) {
  const display = value ?? planning;
  return <>{display == null ? 'Unknown' : metricValue(display, metric, 't CO₂e')}
    {value == null && planning != null && <small>Planning estimate</small>}
  </>;
}

function coverageStatus(row: Row) {
  if (row.planning_kwh == null) return stateLabels[row.state];
  if (row.boundary_id === 'm365:storage-gb-days') return 'Storage only · partial coverage';
  if (row.boundary_id === 'azure_costs:capacity-day') {
    return row.planning_kg_co2e == null ? 'Capacity assumed · grid location needed' : 'Capacity assumed';
  }
  return 'Transmission only · grid location needed';
}

function Table({ run, rows }: { run: string; rows: Row[] }) {
  const gaps = rows.filter(row => row.state !== 'estimated').length;
  return <>
    <p>{number.format(rows.length)} workload boundaries. {number.format(gaps)} have a gap or partial activity. Planning estimates cover only the activity shown and are outside the baseline totals.</p>
    <div className="table-scroll dashboard-table-scroll" tabIndex={0} aria-label="Electricity and emissions coverage">
      <table className="dashboard-table">
        <thead><tr><th scope="col">Workload</th><th scope="col">Location</th><th scope="col">Activity</th>
          <th scope="col">Electricity</th><th scope="col">Emissions</th><th scope="col">Status</th>
          <th scope="col">Factors and evidence</th></tr></thead>
        <tbody>{rows.map(row => <tr key={[row.boundary_id, row.provider, row.tool, row.location].join('|')}>
          <th scope="row">{row.tool}<small>{row.provider} · {row.boundary_id}</small></th>
          <td>{row.location}</td>
          <td>{row.activity_quantity === null ? 'Unknown' :
            `${number.format(Number(row.activity_quantity))} ${row.activity_unit ?? ''}`}</td>
          <td><Estimate value={row.energy_kwh} planning={row.planning_kwh} metric="energy" /></td>
          <td><Estimate value={row.reporting_kg_co2e} planning={row.planning_kg_co2e} metric="carbon" /></td>
          <td>{coverageStatus(row)}
            {row.months_missing_activity > 0 && row.state !== 'missing_activity' &&
              <small>{row.months_missing_activity} of {row.months} months lack activity</small>}</td>
          <td>{row.factor_sources.map(factor => <small key={factor.factor_id}>
            {/^https?:/.test(factor.source_reference) ?
              <a href={factor.source_reference} target="_blank" rel="noreferrer">{factor.factor_name}</a> : factor.factor_name}
          </small>)}
            <Evidence run={run} id={row.evidence_set_id} label="Activity records" /></td>
        </tr>)}</tbody>
      </table>
    </div>
  </>;
}

export default function DashboardCoverage({ run, scenario }: { run: string; scenario: Scenario }) {
  const [open, setOpen] = useState(false);
  const coverage = useGold<Row[]>(`/runs/${run}/coverage?scenario=${scenario}`, open);
  return <section className="dashboard-panel" aria-label="Electricity and emissions coverage">
    <details className="dashboard-disclosure" onToggle={event => setOpen(event.currentTarget.open)}>
      <summary>Coverage by workload: activity, factor and gaps</summary>
      {open && <DashboardRequest query={coverage} label="coverage">{rows => <Table run={run} rows={rows} />}</DashboardRequest>}
    </details>
  </section>;
}
