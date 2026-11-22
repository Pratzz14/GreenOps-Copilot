import { useId } from 'react';
import { dateLabel, sumAvailable } from './dashboardData';
import RecommendationMonthlyImpact from './RecommendationMonthlyImpact';
import { spending, type RecommendationGroup } from './recommendationData';

function licenceComparison(row: RecommendationGroup, annual: number, quantified: number) {
  if (row.action !== 'resize') return null;
  const scopes = row.members.flatMap(member => {
    const licence = member.licence_spend;
    if (member.safety_status === 'blocked' || licence?.annual == null || Number(licence.annual) <= 0) return [];
    return [{ licence, removable: member.persistent_unused ?? 0 }];
  });
  const priced = scopes.flatMap(({ licence, removable }) => {
    const seats = licence.purchased_seats;
    if (seats == null || licence.unit_chf == null || removable > seats) return [];
    return [{ seats, removable, monthlyCost: seats * Number(licence.unit_chf) }];
  });
  if (!priced.length || priced.length !== quantified || scopes.length !== quantified ||
      Math.abs(scopes.reduce((sum, scope) => sum + Number(scope.licence.annual), 0) - annual) >= 0.005) return null;
  const seats = priced.reduce((sum, scope) => sum + scope.seats, 0);
  const removable = priced.reduce((sum, scope) => sum + scope.removable, 0);
  const current = priced.reduce((sum, scope) => sum + scope.monthlyCost, 0);
  const proposed = current - annual / 12;
  return current > 0 && proposed >= 0 ? { seats, removable, current, proposed } : null;
}

function impactTiming(row: RecommendationGroup) {
  if (row.action !== 'resize') return 'Confirm the implementation date before budgeting these savings.';
  const licences = row.members
    .filter(member => member.safety_status !== 'blocked' && Number(member.licence_spend?.annual) > 0)
    .map(member => member.licence_spend);
  const deadline = licences[0]?.notice_deadline;
  if (deadline && licences.every(licence => !licence?.effective_date && licence?.notice_deadline === deadline)) {
    return `The ${dateLabel.format(new Date(deadline))} notice deadline had passed as of the published decision date. Confirm the next eligible renewal with Procurement.`;
  }
  return 'Confirm when the seats can be reduced with Procurement before budgeting these savings.';
}

export default function RecommendationImpact({ row }: { row: RecommendationGroup }) {
  const titleId = useId();
  if (row.safety_counts.blocked === row.members.length) {
    return <p>This action is blocked.</p>;
  }
  if (row.spending_projection) return <RecommendationMonthlyImpact projection={row.spending_projection} />;

  const estimate = row.savings.steady_state.net_chf;
  const annual = sumAvailable(estimate?.eligible, estimate?.conditional);
  if (annual === null || !Number.isFinite(annual) || annual <= 0) {
    return <p>No positive net spending savings have been quantified for this recommendation.</p>;
  }
  const quantified = estimate?.quantified ?? 0;
  const comparison = licenceComparison(row, annual, quantified);
  return <section className="recommendation-impact" aria-labelledby={titleId}>
    <header className="recommendation-impact-header">
      <div>
        <h3 id={titleId}>Estimated spending impact</h3>
        <p>{comparison ? 'Monthly spend at the latest published seat prices' : 'Savings at the modeled rate after implementation'}</p>
      </div>
      <div className="recommendation-impact-total">
        <strong>{spending(annual / 12)} / month</strong>
        <small>{spending(annual)} annualized savings</small>
      </div>
    </header>
    {comparison && <dl className="recommendation-impact-costs" aria-label="Modeled monthly spending comparison">
      {[
        { label: 'Current setup', seats: comparison.seats, amount: comparison.current },
        { label: 'If followed', seats: comparison.seats - comparison.removable, amount: comparison.proposed },
      ].map(({ label, seats, amount }) => <div key={label}>
        <dt>{label} <small>{seats} {seats === 1 ? 'seat' : 'seats'}</small></dt>
        <dd>{spending(amount)}</dd>
      </div>)}
    </dl>}
    <p className="recommendation-impact-note">{impactTiming(row)}</p>
    {(estimate?.conditional != null || quantified < row.members.length) && <p className="recommendation-impact-note">
      {estimate?.conditional != null && 'Includes savings subject to review. '}
      {quantified < row.members.length && `Covers ${quantified} of ${row.members.length} supporting scopes.`}
    </p>}
  </section>;
}
