import { useState } from 'react';
import { useGold } from './api/gold';
import type { components } from './api/schema';
import { CalculationFactors, Evidence } from './GoldEvidence';
import GoldTables from './GoldTables';
import { LayerDisclosure, LayerSummary } from './LayerOverview';
import { chfFormat as money, numberFormat as number, numberLocale } from './numberFormat';

type Models = components['schemas'];
type Scenario = Models['GoldScore']['scenario'];
type Horizon = Models['GoldScore']['horizon'];
type Group = 'department' | 'tool' | 'provider' | 'location';

const root = '/api/v1';
const percent = new Intl.NumberFormat(numberLocale, { style: 'percent', maximumFractionDigits: 1, signDisplay: 'auto' });
const dateLabel = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });
const statuses = {
  unassessed: 'Targets unassessed',
  meets_targets: 'Meets targets',
  misses_targets: 'Misses targets',
  conditional: 'Human review required',
  blocked: 'Blocked',
  human_review: 'Human review',
  eligible: 'Eligible',
  complete: 'Complete coverage',
  partial: 'Partial coverage',
  unknown: 'Coverage unknown',
};
const groups: Record<Group, string> = {
  department: 'Department', tool: 'Tool', provider: 'Provider', location: 'Location',
};

function display(value: string | number | null, formatter = number) {
  return value === null ? '—' : formatter.format(Number(value));
}

function Baseline({ overview }: { overview: Models['GoldOverview'] }) {
  const { cost, energy, emissions } = overview;
  const metrics = [
    ['Recorded spending', display(cost.value, money), overview.cost_coverage],
    ['Estimated electricity', `${display(energy.value)}${energy.value === null ? '' : ' kWh'}`, overview.energy_coverage],
    ['Estimated location-based emissions', `${display(emissions.value)}${emissions.value === null ? '' : emissions.unit === 'kg_CO2' ? ' kg CO₂' : ' kg CO₂e'}`, overview.carbon_coverage],
  ] as const;
  const scenario = overview.context.scenario;
  const scenarioLabel = scenario[0].toUpperCase() + scenario.slice(1);
  return <LayerSummary label="Gold baseline" metrics={metrics.map(([label, value, coverage], index) => ({
    label, value, note: index ? `${scenarioLabel} scenario · ${statuses[coverage]}` : undefined,
  }))}>
    <div className="layer-summary-status">
      <strong>{number.format(overview.included_rows)} recorded charges</strong>
      <span>{number.format(overview.missing_amount_rows)} missing amounts · {number.format(overview.missing_fx_rows)} missing exchange rates
        {' · '}{number.format(overview.review_rows)} dated charges under review.</span>
    </div>
  </LayerSummary>;
}

function Breakdown({ run, scenario }: { run: string; scenario: Scenario }) {
  const [group, setGroup] = useState<Group>('department');
  const [month, setMonth] = useState('');
  const result = useGold<Models['GoldBreakdown'][]>(`/runs/${run}/breakdowns?group=${group}&scenario=${scenario}`);
  const rows = result.data ?? [];
  const months = [...new Set(rows.flatMap(row => row.report_month ? [row.report_month] : []))];
  const visible = rows.filter(row => (row.report_month ?? '') === month);
  return <section className="panel gold-section" aria-labelledby="gold-breakdown">
    <div className="gold-section-heading">
      <h2 id="gold-breakdown">Spending and footprint</h2>
      <div className="gold-controls">
        <label>Group by<select value={group} onChange={event => { setGroup(event.target.value as Group); setMonth(''); }}>
          {Object.entries(groups).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>Period<select value={month} onChange={event => setMonth(event.target.value)}>
          <option value="">Baseline year</option>
          {months.map(value => <option key={value} value={value}>{value.slice(0, 7)}</option>)}
        </select></label>
      </div>
    </div>
    {result.isError ? <p role="alert">{result.error.message}</p> : result.isPending ?
      <p role="status">Loading breakdown…</p> : (
      <div className="table-scroll" tabIndex={0} aria-label="Spending and footprint table">
        <table className="gold-table"><thead><tr>
          <th scope="col">{groups[group]}</th><th scope="col">Recorded CHF</th><th scope="col">Estimated kWh</th>
          <th scope="col">Estimated kg CO₂</th><th scope="col">Imputed CHF</th>
          <th scope="col">Swiss operating kg CO₂e</th><th scope="col">Open cost records</th><th scope="col">CO₂ coverage</th>
        </tr></thead><tbody>{visible.map(row => <tr key={row.driver}>
          <th scope="row">{row.driver}</th><td>{display(row.recorded_cost_chf, money)}</td><td>{display(row.estimated_kwh)}</td>
          <td>{display(row.estimated_location_kg)}</td><td>{display(row.imputed_cost_chf ?? null, money)}</td>
          <td>{display(row.swiss_operating_kg_co2e ?? null)}</td><td>{number.format(row.unresolved_cost_rows)}</td>
          <td>{row.estimated_location_kg === null ? 'Unknown' : row.incomplete_carbon_buckets ? 'Partial' : 'Complete'}</td>
        </tr>)}</tbody></table>
        {!visible.length ? <p className="empty">No records for this period.</p> : null}
      </div>
    )}
  </section>;
}

function Scorecard({ result, scenario, horizon }: { result: Models['GoldPackage']; scenario: Scenario; horizon: Horizon }) {
  const score = result.scores.find(row => row.scenario === scenario && row.horizon === horizon);
  if (!score) return <p>No score is available for this scenario.</p>;
  const members = result.members.filter(row => row.scenario === scenario && row.horizon === horizon);
  const emissionsUnit = result.emissions_basis === 'CO2' ? 'kg CO₂' : 'kg CO₂e';
  const values = [
    ['Net CHF savings', display(score.net_savings_chf, money), `${display(result.cost_target, percent)} annual target`],
    ['Location-based CO₂ savings', `${display(score.savings_location_kg)} ${emissionsUnit}`, `${display(result.carbon_target, percent)} annual target`],
    ['Implementation cost', display(score.implementation_chf, money), `${display(result.implementation_cap_chf, money)} maximum`],
  ];
  const isAssessable = score.target_status === 'meets_targets' || score.target_status === 'misses_targets';
  return <>
    <span className={`gold-tag gold-tag-${score.target_status}`}>{statuses[score.target_status]}</span>
    <p className="gold-coverage">{result.candidate_set_note}</p>
    {score.evaluation_start && score.evaluation_end_exclusive ? (
      <p className="gold-coverage">{dateLabel.format(new Date(score.evaluation_start))} to {dateLabel.format(new Date(new Date(score.evaluation_end_exclusive).getTime() - 86400000))}</p>
    ) : null}
    <dl className="gold-score-grid">{values.map(([label, value, target]) => <div key={label}>
      <dt>{label}</dt><dd>{value}</dd><small>{target}</small>
    </div>)}</dl>
    {isAssessable ? <p className="gold-coverage">
      Cost margin {display(score.cost_margin_chf, money)} · CO₂ margin {display(score.carbon_margin_kg)} {emissionsUnit}
      {' · '}Budget remaining {display(score.budget_remaining_chf, money)}.
      {score.meets_all_three_scenarios ? ' Meets all three scenarios.' : ''}
    </p> : null}
    {members.length ? <ul className="gold-members">{members.map(row => (
      <li key={row.measure_id}><strong>{row.description}</strong> · {display(row.credited_cost_chf, money)} · {display(row.credited_location_kg)} {emissionsUnit}
        <Evidence run={result.run_id} id={row.evidence_set_id} />
      </li>
    ))}</ul> : null}
  </>;
}

function Findings({ run }: { run: string }) {
  const result = useGold<Models['GoldFinding'][]>(`/runs/${run}/findings`);
  const ordered = result.data && [...result.data].sort((a, b) =>
    Number(b.finding_id === 'development-idle') - Number(a.finding_id === 'development-idle'));
  return <section className="panel gold-section">
    <h2>Waste findings</h2>
    {result.isError ? <p role="alert">{result.error.message}</p> : !ordered ?
      <p role="status">Loading findings…</p> : <div className="gold-findings">
        {ordered.map(finding => (
          <article className="gold-item" key={finding.finding_id}>
            <h3>{finding.subject_name}</h3>
            <p>{finding.observed_fact}</p>
            <p className="gold-coverage">{finding.waste_hypothesis}</p>
            <Evidence run={run} id={finding.evidence_set_id} />
          </article>
        ))}
      </div>}
  </section>;
}

function Safety({ run, scenario, horizon }: { run: string; scenario: Scenario; horizon: Horizon }) {
  const result = useGold<Models['GoldSafety']>(`/runs/${run}/safety-decisions`);
  const [showRules, setShowRules] = useState(false);
  const decisions = result.data && [...result.data.decisions].sort((a, b) =>
    Number(b.measure_id === 'shutdown-production') - Number(a.measure_id === 'shutdown-production'));
  const localDate = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Zurich' });
  return <section className="panel gold-section">
    <h2>Safety decisions</h2>
    {result.isError ? <p role="alert">{result.error.message}</p> : !decisions ?
      <p role="status">Loading safety decisions…</p> : decisions.map(decision => {
        const estimate = decision.estimates.find(row => row.scenario === scenario && row.horizon === horizon);
        return <article className="gold-item" key={decision.measure_id}>
          <div className="gold-section-heading"><h3>{decision.description}</h3>
            <span className={`gold-tag gold-tag-${decision.safety_status}`}>{statuses[decision.safety_status]}</span>
          </div>
          <p>{decision.risks_and_exceptions}</p>
          {decision.responsible_role ? <p className="gold-coverage">Review owner · {decision.responsible_role}</p> : null}
          {decision.notice_deadline ? <p className="gold-coverage">Indicative notice deadline · {dateLabel.format(new Date(decision.notice_deadline))}</p> : null}
          {estimate && (estimate.net_chf !== null || estimate.savings_location_kg !== null) ? (
            <p className="gold-coverage">Illustrative savings · {display(estimate.net_chf, money)} · {display(estimate.savings_location_kg)} kg CO₂
              {decision.effort_person_days ? ` · ${display(decision.effort_person_days)} person-days` : ''}
            </p>
          ) : null}
          <Evidence run={run} id={decision.evidence_set_id} />
        </article>;
      })}
    {result.data?.protections.length ? <details className="gold-evidence" onToggle={event => setShowRules(event.currentTarget.open)}>
      <summary>Protection windows</summary>
      {showRules ? <ul>{result.data.protections.map(rule => (
        <li key={rule.evidence_set_id}>
          <strong>{rule.subject_name}</strong> · {rule.action_scope}
          {rule.starts_at && rule.ends_at ?
            ` · ${localDate.format(new Date(rule.starts_at))} – ${localDate.format(new Date(rule.ends_at))} Zurich time` : ''}
          <p>{rule.reason}</p>
          <Evidence run={run} id={rule.evidence_set_id} />
        </li>
      ))}</ul> : null}
    </details> : null}
  </section>;
}

function Factors({ run }: { run: string }) {
  const [open, setOpen] = useState(false);
  return <details className="panel gold-section gold-evidence" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Factors and calculation assumptions</summary>
    {open && <CalculationFactors run={run} />}
  </details>;
}

function GoldDetails({ run, scenario, setScenario, overview, open }: {
  run: Models['GoldRun'];
  scenario: Scenario;
  setScenario: (scenario: Scenario) => void;
  overview?: Models['GoldOverview'];
  open: boolean;
}) {
  const [horizon, setHorizon] = useState<Horizon>('steady_state');
  const [showConditional, setShowConditional] = useState(false);
  const packageResult = useGold<Models['GoldPackage']>(`/packages/${run.package_id}`, open);
  const conditional = useGold<Models['GoldPackage']>(`/packages/${run.conditional_package_id}`,
    open && showConditional && run.conditional_package_id !== null);
  const draft = packageResult.data?.selection_status === 'provisional' || packageResult.data?.selection_status === 'pending';
  return <>
    <div className="gold-controls">
      <label>Assumption scenario<select value={scenario} onChange={event => setScenario(event.target.value as Scenario)}>
        <option value="low">Low</option><option value="mid">Mid</option><option value="high">High</option>
      </select></label>
      {overview && overview.carbon_coverage !== 'complete' ?
        <p className="gold-coverage">Emissions include workloads with a compatible grid factor.</p> : null}
    </div>
    <Breakdown run={run.run_id} scenario={scenario} />
    <section className="panel gold-section" aria-labelledby="gold-package">
      <div className="gold-section-heading"><h2 id="gold-package">Savings package</h2>
        <label>Savings horizon<select value={horizon} onChange={event => setHorizon(event.target.value as Horizon)}>
          <option value="steady_state">Steady-state annual</option><option value="first_year">First 12 months</option>
        </select></label>
      </div>
      {packageResult.isError ? <p role="alert">{packageResult.error.message}</p> : !packageResult.data ?
        <p role="status">Loading package…</p> : <>
          <Scorecard result={packageResult.data} scenario={scenario} horizon={horizon} />
          <div className="gold-downloads">
            <a href={`${root}/packages/${run.package_id}/exports/baseline.csv`}>{draft ? 'Draft baseline CSV' : 'Baseline CSV'}</a>
            <a href={`${root}/packages/${run.package_id}/exports/measures.csv`}>{draft ? 'Draft measures CSV' : 'Measures CSV'}</a>
            <small>Submission exports use the mid scenario and steady-state annual savings.</small>
          </div>
        </>}
      {run.conditional_package_id ? <details className="gold-evidence" onToggle={event => setShowConditional(event.currentTarget.open)}>
        <summary>Conditional package illustration</summary>
        {showConditional ? conditional.isError ? <p role="alert">{conditional.error.message}</p> : conditional.data ?
          <>
            <Scorecard result={conditional.data} scenario={scenario} horizon={horizon} />
            <div className="gold-downloads">
              <a href={`${root}/packages/${conditional.data.package_id}/exports/measures.csv`}>Conditional draft measures CSV</a>
              <small>Mid assumptions and annual run rate.</small>
            </div>
          </> :
          <p role="status">Loading illustration…</p> : null}
      </details> : null}
    </section>
    <Findings run={run.run_id} />
    <Safety run={run.run_id} scenario={scenario} horizon={horizon} />
    <Factors run={run.run_id} />
    <details className="provenance">
      <summary>Run provenance</summary>
      <p>Decision date {dateLabel.format(new Date(run.decision_as_of))} · Gold run <code>{run.run_id}</code></p>
      <p>Silver version <code>{run.data_version}</code> · Factor version <code>{run.factor_version}</code></p>
      {overview ? <Evidence run={run.run_id} id={overview.evidence_set_id} /> : null}
    </details>
  </>;
}

function GoldRun({ run, initialTable }: { run: Models['GoldRun']; initialTable?: string }) {
  const [scenario, setScenario] = useState<Scenario>('mid');
  const overview = useGold<Models['GoldOverview']>(`/runs/${run.run_id}/overview?scenario=${scenario}`);
  return <div className="layer-dashboard">
    <header className="layer-heading">
      <h1>Business insights and decisions.</h1>
      <p>{dateLabel.format(new Date(run.period_start))} – {dateLabel.format(new Date(run.period_end))}</p>
    </header>
    {overview.isError ? <p role="alert">{overview.error.message}</p> : !overview.data ?
      <p role="status">Loading baseline…</p> : <Baseline overview={overview.data} />}
    <div className="layer-actions">
      <GoldTables runId={run.run_id} initialTable={initialTable} />
      <LayerDisclosure title="Detailed overview" description="Spending and footprint, savings, findings, and safety decisions.">
        {open => <GoldDetails run={run} scenario={scenario} setScenario={setScenario} overview={overview.data} open={open} />}
      </LayerDisclosure>
    </div>
  </div>;
}

export default function Gold({ initialTable }: { initialTable?: string }) {
  const current = useGold<Models['GoldRun']>('/runs/current');
  if (current.data) return <GoldRun key={current.data.run_id} run={current.data} initialTable={initialTable} />;
  return <section className="layer-dashboard layer-heading">
    <div>
      <h1>Business insights and decisions.</h1>
      {current.isError ? <div className="error-panel" role="alert">
        <p>{current.error.message}</p>
        <button type="button" onClick={() => void current.refetch()}>Retry</button>
      </div> : <p role="status">Loading Gold run…</p>}
    </div>
  </section>;
}
