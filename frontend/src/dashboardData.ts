import type { components } from './api/schema';
import { formatCount, numberFormat, numberLocale } from './numberFormat';

export type GoldModels = components['schemas'];
export type Scenario = GoldModels['GoldScore']['scenario'];
export type Breakdown = GoldModels['GoldBreakdown'];
export type Metric = 'carbon' | 'energy' | 'cost';
export type Group = 'tool' | 'platform' | 'department' | 'provider' | 'location';
export type CarbonUnit = 't CO₂' | 't CO₂e';

export const number = numberFormat;
const monthName = new Intl.DateTimeFormat('en-GB', { month: 'short', timeZone: 'UTC' });
const monthAndYear = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
export const dateLabel = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });
export const percent = new Intl.NumberFormat(numberLocale, { style: 'percent', maximumFractionDigits: 1 });

export const metricLabels: Record<Metric, string> = { carbon: 'Emissions', energy: 'Energy', cost: 'Spending' };
export const groupLabels: Record<Group, string> = {
  tool: 'Tool', platform: 'Platform', provider: 'Provider', location: 'Location', department: 'Department',
};
export const coverageLabels = { complete: 'Complete coverage', partial: 'Partial coverage', unknown: 'Coverage unknown' };
export const dashboardDefaults = {
  scenario: 'mid' as Scenario,
  group: 'tool' as Group,
  metric: 'cost' as Metric,
  period: null as string[] | null,
  driver: '',
};

export type DashboardFilters = typeof dashboardDefaults;

export function monthLabel(month: string, withYear = true) {
  return (withYear ? monthAndYear : monthName).format(new Date(month));
}

export function baselineMonths(start: string, end: string) {
  const month = new Date(start);
  const last = new Date(end);
  month.setUTCDate(1);
  const months: string[] = [];
  while (month <= last) {
    months.push(month.toISOString().slice(0, 10));
    month.setUTCMonth(month.getUTCMonth() + 1);
  }
  return months;
}

export function carbonUnit(basis: string | undefined): CarbonUnit {
  return basis === 'CO2e' || basis === 'kg_CO2e' ? 't CO₂e' : 't CO₂';
}

export function emissionsUnit(overview: GoldModels['GoldOverview'] | undefined): CarbonUnit {
  return overview ? 't CO₂e' : carbonUnit(undefined);
}

export function metricUnit(metric: Metric, emissionsUnit: CarbonUnit) {
  return metric === 'carbon' ? emissionsUnit : metric === 'cost' ? 'CHF' : 'kWh';
}

export function metricValue(value: string | number | null, metric: Metric, emissionsUnit: CarbonUnit) {
  if (value === null) return 'Unavailable';
  const numeric = Number(value);
  if (metric === 'cost') return `CHF ${formatCount(numeric)}`;
  if (metric === 'energy') return `${formatCount(numeric)} kWh`;
  if (numeric !== 0 && Math.abs(numeric) < 5) return `${number.format(numeric)} kg ${emissionsUnit.slice(2)}`;
  return `${number.format(numeric / 1000)} ${emissionsUnit}`;
}

export function sumAvailable(first: string | number | null | undefined, second: string | number | null | undefined) {
  return first == null && second == null ? null : Number(first ?? 0) + Number(second ?? 0);
}

export function rowValue(row: Breakdown, metric: Metric) {
  if (metric === 'carbon') return row.reporting_kg_co2e == null ? null : Number(row.reporting_kg_co2e);
  if (metric === 'cost') return sumAvailable(row.recorded_cost_chf, row.imputed_cost_chf);
  return row.estimated_kwh === null ? null : Number(row.estimated_kwh);
}

function incompleteRows(row: Breakdown, metric: Metric) {
  return metric === 'carbon' ? row.incomplete_carbon_buckets :
    metric === 'energy' ? row.incomplete_energy_buckets : row.unresolved_cost_rows;
}

export function rowCoverage(row: Breakdown, metric: Metric) {
  if (rowValue(row, metric) === null) return 'unknown';
  return incompleteRows(row, metric) > 0 ? 'partial' : 'complete';
}

export function periodBreakdown(rows: Breakdown[], period: string[] | null) {
  if (period === null) return rows.filter(row => row.report_month === null);
  const months = new Set(period);
  const totals = new Map<string, Breakdown>();
  function sum(a: string | null | undefined, b: string | null | undefined) {
    const total = sumAvailable(a, b);
    return total === null ? null : String(total);
  }
  for (const row of rows) {
    if (!row.report_month || !months.has(row.report_month)) continue;
    const previous = totals.get(row.driver);
    totals.set(row.driver, previous ? {
      ...previous,
      reporting_kg_co2e: sum(previous.reporting_kg_co2e, row.reporting_kg_co2e),
      planning_kwh: sum(previous.planning_kwh, row.planning_kwh),
      planning_kg_co2e: sum(previous.planning_kg_co2e, row.planning_kg_co2e),
      planning_energy_boundaries: [...new Set([
        ...(previous.planning_energy_boundaries ?? []), ...(row.planning_energy_boundaries ?? []),
      ])],
      needs_energy_factor: previous.needs_energy_factor || row.needs_energy_factor,
      estimated_location_kg: sum(previous.estimated_location_kg, row.estimated_location_kg),
      estimated_kwh: sum(previous.estimated_kwh, row.estimated_kwh),
      recorded_cost_chf: sum(previous.recorded_cost_chf, row.recorded_cost_chf),
      imputed_cost_chf: sum(previous.imputed_cost_chf, row.imputed_cost_chf),
      recovered_cost_chf: sum(previous.recovered_cost_chf, row.recovered_cost_chf),
      swiss_operating_kg_co2e: sum(previous.swiss_operating_kg_co2e, row.swiss_operating_kg_co2e),
      unresolved_cost_rows: previous.unresolved_cost_rows + row.unresolved_cost_rows,
      incomplete_carbon_buckets: previous.incomplete_carbon_buckets + row.incomplete_carbon_buckets,
      incomplete_energy_buckets: previous.incomplete_energy_buckets + row.incomplete_energy_buckets,
    } : row);
  }
  return [...totals.values()];
}

export function trendPoints(rows: Breakdown[], months: string[], metric: Metric, driver: string) {
  const totals = new Map<string, { total: number | null; partial: boolean }>();
  for (const row of rows) {
    if (!row.report_month || (driver && row.driver !== driver)) continue;
    const value = rowValue(row, metric);
    const previous = totals.get(row.report_month);
    totals.set(row.report_month, {
      total: value === null ? previous?.total ?? null : (previous?.total ?? 0) + value,
      partial: Boolean(previous?.partial || incompleteRows(row, metric) > 0),
    });
  }
  return months.map(month => {
    const point = totals.get(month);
    return { month, value: point?.total ?? null, partial: point?.partial ?? false };
  });
}
