import { carbonUnit, metricValue, type GoldModels, type Metric } from './dashboardData';
import { chfFormat } from './numberFormat';

export type Recommendation = GoldModels['GroupedRecommendationMember'];
export type RecommendationGroup = GoldModels['RecommendationGroup'];
export const fields = { cost: 'net_chf', energy: 'savings_kwh', carbon: 'savings_location_kg' } as const;
export const labels = { cost: 'Net cost', energy: 'Energy', carbon: 'Location-based emissions' };
export const statuses = { eligible: 'Eligible', human_review: 'Needs review', blocked: 'Blocked' };

export function spending(value: string | number) {
  return chfFormat.format(Number(value));
}

export function memberSavings(row: Recommendation, metric: Metric, month = '', horizon = 'steady_state') {
  if (row.safety_status === 'blocked') return { amount: null, reason: 'Blocked' };
  if (month) {
    const period = row.monthly_spend.find(item => item.month === month);
    return { amount: period?.amount ?? null, reason: period?.reason ?? 'No estimate for this month' };
  }
  if (row.licence_spend && metric === 'cost') {
    return { amount: row.licence_spend[horizon === 'first_year' ? 'first_year' : 'annual'],
      reason: row.licence_spend.reason ?? 'Renewal date unconfirmed' };
  }
  const value = row.estimate?.estimates.find(item => item.horizon === horizon)?.[fields[metric]];
  return { amount: row.metric_gaps[fields[metric]] ? null : value ?? null,
    reason: row.metric_gaps[fields[metric]] ?? 'No estimate available' };
}

export function displaySavings(value: ReturnType<typeof memberSavings>, metric: Metric, basis: string) {
  if (value.amount === null) return value.reason;
  return metric === 'cost' ? spending(value.amount) : metricValue(value.amount, metric, carbonUnit(basis));
}

export function groupSavings(row: RecommendationGroup, metric: Metric, month: string) {
  return month ? row.monthly_spend[month] : row.savings.steady_state[fields[metric]];
}
