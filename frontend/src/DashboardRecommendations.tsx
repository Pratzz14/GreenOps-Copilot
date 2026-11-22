import { Fragment, useId, useState } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { useGold } from './api/gold';
import DashboardRequest from './DashboardRequest';
import DashboardPagination from './DashboardPagination';
import { Evidence } from './GoldEvidence';
import { carbonUnit, groupLabels, metricValue, monthLabel, dateLabel, sumAvailable, type GoldModels, type Group, type Metric } from './dashboardData';
import {
  displaySavings, fields, groupSavings, labels, memberSavings, recommendationActions, spending, statuses, type Recommendation, type RecommendationGroup,
} from './recommendationData';

const recommendationPageSize = 5;
const reasons: Record<string, string> = {
  dependency: 'Review dependencies', schedule: 'Review the operating schedule', contract: 'Review contract terms',
  estimate_coverage: 'Verify incomplete savings estimates', rule_eligibility: 'Consistent with the published safety rules',
};

function safetyReason(row: Recommendation) {
  const ruleReason = row.safety_reason?.trim();
  if (row.safety_status === 'blocked') {
    return ruleReason || row.next_check?.trim() || 'A published safety rule blocks this action.';
  }
  const tag = row.ai_tag;
  const reviewReason = row.rule_status === 'eligible' && tag?.decision === 'human_review' ? reasons[tag.reason] : undefined;
  return tag?.explanation || reviewReason || ruleReason || row.next_check?.trim() || 'No reason recorded';
}

function ObservationSources({ run, id }: { run: string; id: string }) {
  const [open, setOpen] = useState(false);
  const sources = useGold<GoldModels['RecommendationEvidence'][]>(
    `/runs/${run}/recommendations/${id}/evidence`, open,
  );
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Recurrence source rows</summary>
    {open && <DashboardRequest query={sources} label="recurrence evidence">{rows => {
      const grouped = new Map<string, number[]>();
      for (const { file, row } of rows) {
        const numbers = grouped.get(file) ?? [];
        numbers.push(row);
        grouped.set(file, numbers);
      }
      return <ul>{Array.from(grouped, ([file, numbers]) => <li key={file}>{file} · {numbers.join(', ')}</li>)}</ul>;
    }}</DashboardRequest>}
  </details>;
}

function RecommendationDetails({ row, run, basis }: { row: Recommendation; run: string; basis: string }) {
  const annual = row.estimate?.estimates.find(item => item.horizon === 'steady_state');
  return <div className="dashboard-recommendation-details">
    {row.persistent_unused !== null && <p>{row.persistent_unused} persistently unused seats</p>}
    <p>{row.proposed_change}</p>
    <p>{row.months[0]} through {row.months.at(-1)} · {row.months.length} months with qualifying evidence</p>
    {annual?.estimate_status === 'conditional' && <p>Conditional savings estimate</p>}
    <dl className="dashboard-recommendation-savings">
      {(Object.keys(fields) as Metric[]).map(key => <div key={key}>
        <dt>{labels[key]}</dt>
        <dd>Annual · {displaySavings(memberSavings(row, key), key, basis)}</dd>
        <dd>First year · {displaySavings(memberSavings(row, key, '', 'first_year'), key, basis)}</dd>
      </div>)}
    </dl>
    {row.licence_spend?.unit_chf != null && <p>
      Annual spending uses {row.persistent_unused} persistently unused seats × {spending(row.licence_spend.unit_chf)} per seat in {monthLabel(row.licence_spend.price_month)} × 12.
    </p>}
    {row.licence_spend?.effective_date && !row.estimate?.earliest_effective_date &&
      <p>Earliest modeled start {dateLabel.format(new Date(row.licence_spend.effective_date))}</p>}
    {row.safety_status !== 'blocked' && <details>
      <summary>Monthly spending calculation</summary>
      <ul>{row.monthly_spend.map(period => <li key={period.month}>
        {monthLabel(period.month)} · {period.amount == null ? period.reason : spending(period.amount)}
        {period.unused_seats != null && period.seat_price != null && period.fx_rate != null &&
          <> · {period.unused_seats} unused seats × {period.currency} {period.seat_price} × {period.fx_rate} CHF per {period.currency}</>}
        {period.source_file && <> · {period.source_file} row {period.source_row}</>}
        {period.calculation && <p>{period.calculation}</p>}
        {period.sources?.map(source => <p key={source.file}>{source.file} · Rows {source.rows.join(', ')}</p>)}
      </li>)}</ul>
    </details>}
    {row.estimate?.effort_person_days != null && <p>{row.estimate.effort_person_days} person-days</p>}
    {row.estimate?.earliest_effective_date &&
      <p>Earliest modeled start {dateLabel.format(new Date(row.estimate.earliest_effective_date))}</p>}
    {row.estimate?.notice_deadline && <p>Notice deadline {dateLabel.format(new Date(row.estimate.notice_deadline))}</p>}
    <p><strong>{row.responsible_role}</strong> · {row.next_check}</p>
    <p>Rules · {statuses[row.rule_status]}</p>
    <p>{row.ai_tag ? `AI tag · ${statuses[row.ai_tag.decision]} · ${reasons[row.ai_tag.reason] ?? row.ai_tag.reason}`
      : 'AI tag unavailable'}</p>
    <ObservationSources run={run} id={row.id} />
    {annual && <Evidence run={run} id={annual.evidence_set_id} label="Savings assumptions and sources" />}
    {row.protection_evidence_ids.map((id, index) =>
      <Evidence run={run} id={id} key={id} label={`Protection evidence ${index + 1}`} />)}
  </div>;
}

function MemberEvidence({ row, run, basis, selected }: {
  row: Recommendation; run: string; basis: string; selected: boolean;
}) {
  const [open, setOpen] = useState(selected);
  const period = row.category === 'Licence' ? 'months' : 'weeks';
  return <details className="dashboard-recommendation-member" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>
      <strong>{row.resource}</strong> · {row.qualifying} of {row.observed} {period} qualified
    </summary>
    {open && <RecommendationDetails row={row} run={run} basis={basis} />}
  </details>;
}

function Savings({ row, basis, metric, month }: { row: RecommendationGroup; basis: string; metric: Metric; month: string }) {
  const { eligible, conditional, quantified } = groupSavings(row, metric, month) ?? { eligible: null, conditional: null, quantified: 0 };
  const total = sumAvailable(eligible, conditional);
  const eligibleMembers = row.members.length - (row.safety_counts.blocked ?? 0);
  const format = (amount: string | number) => metric === 'cost' ? spending(amount) : metricValue(amount, metric, carbonUnit(basis));
  const gaps = new Set(row.members.filter(member => member.safety_status !== 'blocked')
    .map(member => memberSavings(member, metric, month).reason));
  return <>
    {total === null && <span>{eligibleMembers
      ? row.omitted_measure_count ? 'Overlapping estimates' : gaps.size === 1 ? [...gaps][0] : 'See missing inputs below'
      : 'Blocked'}</span>}
    {total !== null && <strong>{format(total)}</strong>}
    {conditional !== null && <small>Includes savings subject to review</small>}
    {quantified > 0 && quantified < eligibleMembers && <small>Partial coverage</small>}
  </>;
}

export function RecommendationRow({ row, run, basis, metric, selected, month, scopeFirst = false }: {
  row: RecommendationGroup; run: string; basis: string; metric: Metric; selected: string | null; month: string;
  scopeFirst?: boolean;
}) {
  const [open, setOpen] = useState(row.members.some(member => member.id === selected));
  const detailsId = useId();
  const counts = Object.entries(statuses).filter(([status]) => row.safety_counts[status as keyof typeof statuses]);
  const status = counts.length === 1 ? counts[0][0] : 'mixed';
  const scopeUnit = { schedule: 'cluster', shutdown: 'server', resize: 'licence scope' }[row.action];
  const scopeLabel = row.cost_center_count === row.members.length ? 'cost center' : scopeUnit;
  const owners = [...new Set(row.members.map(member => member.responsible_role))];
  const seatCounts = row.members.map(member => member.monthly_spend.find(item => item.month === month)?.unused_seats);
  const seats = month ? (seatCounts.some(count => count != null) ? seatCounts.reduce<number>((total, count) => total + (count ?? 0), 0) : null)
    : row.persistent_unused;
  const periodLabel = month ? `Monthly savings · ${monthLabel(month)}` : 'Annual savings';
  return <Fragment>
    <tr className="dashboard-recommendation">
      <th scope="row"><button type="button" className="dashboard-recommendation-toggle"
        aria-expanded={open} aria-controls={detailsId} onClick={() => setOpen(value => !value)}>
        <svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16">
          <path d={open ? 'M3 6l5 5 5-5' : 'M6 3l5 5-5 5'} fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <span><strong>{scopeFirst ? row.scope : recommendationActions[row.action]}</strong>
          <small>{scopeFirst ? recommendationActions[row.action] : row.scope}</small></span>
      </button></th>
      <td>{row.members.length} {scopeLabel}{row.members.length === 1 ? '' : 's'}
        {seats !== null && <small>{seats} unused seats</small>}
      </td>
      <td className="dashboard-recommendation-amount"><span className="dashboard-recommendation-mobile-label">{periodLabel}</span>
        <Savings row={row} basis={basis} metric={metric} month={month} />
      </td>
      <td><span className="dashboard-recommendation-status" data-status={status}>
        {counts.length === 1 ? counts[0][1] : 'Mixed'}
      </span>{counts.length > 1 && <small>{counts.map(([key, label]) =>
          `${row.safety_counts[key as keyof typeof statuses]} ${label.toLowerCase()}`).join(' · ')}</small>}</td>
    </tr>
    <tr className="dashboard-recommendation-expansion" id={detailsId} hidden={!open}><td colSpan={4}>
      {open && <div className="dashboard-recommendation-evidence">
        <p><strong>{owners.join(' · ')}</strong>{row.action === 'resize' && <> · Confirm minimum seats and renewal terms.</>}</p>
        {row.persistent_unused !== null && <p>The annual estimate uses {row.persistent_unused} persistently unused seats.</p>}
        {row.omitted_measure_count > 0 && <p>{row.omitted_measure_count} overlapping or shared estimates require individual review.</p>}
        <details><summary>Monthly spending breakdown</summary>
          <ul>{Object.entries(row.monthly_spend).map(([period, totals]) => {
            const total = sumAvailable(totals.eligible, totals.conditional);
            return <li key={period}>
              {monthLabel(period)} · {total === null ? 'No priced estimate' : spending(total)}
              {totals.conditional !== null && ' · Includes savings subject to review'}
            </li>;
          })}</ul>
        </details>
        <table aria-label="Supporting scopes" role="table" className="dashboard-recommendation-members">
          <thead role="rowgroup"><tr role="row"><th scope="col">Supporting scope</th>
            {row.action === 'resize' && <th scope="col">Unused seats</th>}
            <th scope="col">Safety</th><th scope="col">Reason</th><th scope="col">{periodLabel}</th></tr></thead>
          <tbody role="rowgroup">{row.members.map((member, index) => {
            return <tr key={member.id} role="row" data-selected={member.id === selected}>
              <th scope="row" role="rowheader"><MemberEvidence row={member} run={run} basis={basis} selected={member.id === selected} /></th>
              {row.action === 'resize' && <td role="cell" data-label="Unused seats">
                {(month ? seatCounts[index] : member.persistent_unused) ?? 'Unavailable'}
              </td>}
              <td role="cell" data-label="Safety">{statuses[member.safety_status]}</td>
              <td role="cell" data-label="Reason" className="dashboard-recommendation-reason">{safetyReason(member)}</td>
              <td role="cell" data-label={periodLabel}>
                {displaySavings(memberSavings(member, metric, month), metric, basis)}
              </td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
    </td></tr>
  </Fragment>;
}

function Results({ rows, run, basis, metric, selected, monthly }: {
  rows: RecommendationGroup[]; run: string; basis: string; metric: Metric; selected: string | null; monthly: boolean;
}) {
  const month = monthly ? rows[0]?.display_month ?? '' : '';
  const value = (item: RecommendationGroup) => {
    const savings = groupSavings(item, metric, month);
    return sumAvailable(savings?.eligible, savings?.conditional) ?? -Infinity;
  };
  const ordered = [...rows].sort((a, b) => value(b) - value(a) || a.scope.localeCompare(b.scope) || a.id.localeCompare(b.id));
  const [page, setPage] = useState(() => Math.max(0, Math.floor(
    ordered.findIndex(row => row.members.some(member => member.id === selected)) / recommendationPageSize,
  )));
  const offset = page * recommendationPageSize;
  return <>
    {!rows.length && <p className="dashboard-table-message">No recurring issues match the dashboard filters.</p>}
    {rows.length > 0 && <table className="dashboard-recommendations-table" aria-label="Grouped recommendations">
      <thead><tr><th scope="col">Recommended action</th><th scope="col">Affected scope</th>
        <th scope="col" aria-sort="descending">{month ? 'Potential monthly savings' : 'Potential annual savings'}
          <small>{month ? monthLabel(month) : labels[metric]}</small></th><th scope="col">Safety</th></tr></thead>
      <tbody>{ordered.slice(offset, offset + recommendationPageSize).map(row =>
        <RecommendationRow key={row.id} row={row} run={run} basis={basis} metric={metric} selected={selected} month={month} />)}</tbody>
    </table>}
    <DashboardPagination page={page} total={rows.length} pageSize={recommendationPageSize} label="Recommendation pages" onPage={setPage} />
  </>;
}

export default function DashboardRecommendations({ query, run, basis, metric, group, emptyPeriod, selection, filterKey }: {
  query: UseQueryResult<RecommendationGroup[], Error>; run: string; basis: string; metric: Metric; group: Group;
  emptyPeriod: boolean; selection: { id: string; click: number } | null; filterKey: string;
}) {
  const [monthlySpending, setMonthlySpending] = useState(true);
  const monthly = metric === 'cost' && monthlySpending;
  const rows = !emptyPeriod && !query.isError ? query.data : undefined;
  return <section id="dashboard-recommendations" className="dashboard-panel dashboard-data-panel dashboard-recommendations"
    aria-labelledby="recommendations-heading" tabIndex={-1}>
    <header className="dashboard-data-header">
      <div>
        <h2 id="recommendations-heading">Recommendations</h2>
        <p>Grouped by {groupLabels[group].toLowerCase()}</p>
        {!!rows?.length && <p>{rows.length} recommendations · {rows.reduce((count, row) => count + row.members.length, 0)} supporting scopes</p>}
      </div>
      {metric === 'cost' && !emptyPeriod && <label className="dashboard-recommendation-period">Spending horizon
        <select value={monthlySpending ? 'month' : 'year'} onChange={event => setMonthlySpending(event.target.value === 'month')}>
          <option value="month">Monthly</option><option value="year">Annual</option>
        </select>
      </label>}
    </header>
    {emptyPeriod ? <p className="dashboard-table-message">Select at least one month to view recommendations.</p> :
      <DashboardRequest query={query} label="recommendations">{rows =>
        <Results key={JSON.stringify([filterKey, metric, selection, monthly])}
          rows={rows} run={run} basis={basis} metric={metric} selected={selection?.id ?? null} monthly={monthly} />
      }</DashboardRequest>}
  </section>;
}
