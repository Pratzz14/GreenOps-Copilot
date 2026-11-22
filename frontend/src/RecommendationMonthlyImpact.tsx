import { useId } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { dateLabel, monthLabel, type GoldModels } from './dashboardData';
import { numberFormat } from './numberFormat';
import { spending } from './recommendationData';

const series = [
  { key: 'published', label: 'Published spend', color: '#2366b9' },
  { key: 'current', label: 'Current setup', color: '#697570' },
  { key: 'followed', label: 'If followed', color: '#217344', dash: '6 4' },
] as const;

export default function RecommendationMonthlyImpact({ projection }: {
  projection: GoldModels['RecommendationSpendingProjection'];
}) {
  const titleId = useId();
  const forecastStart = projection.forecast[0].month;
  const forecastEnd = projection.forecast.at(-1)?.month ?? forecastStart;
  const points = [
    ...projection.history.map(point => ({
      month: point.month, published: Number(point.published_chf), current: null, followed: null,
    })),
    ...projection.forecast.map(point => ({
      month: point.month, published: null, current: Number(point.current_chf), followed: Number(point.if_followed_chf),
    })),
  ];
  const handoff = projection.history.at(-1)?.month;
  const plot = points.map(point => point.month === handoff
    ? { ...point, current: point.published, followed: point.published }
    : point);
  return <section className="recommendation-impact" aria-labelledby={titleId}>
    <header className="recommendation-impact-header">
      <div>
        <h3 id={titleId}>Monthly spending comparison</h3>
        <p>CHF per month · estimates start {monthLabel(forecastStart)}</p>
      </div>
      <div className="recommendation-impact-total">
        <strong>{spending(projection.savings_chf)}</strong>
        <small>Estimated savings · {monthLabel(forecastStart)}–{monthLabel(forecastEnd)}</small>
      </div>
    </header>
    <ul className="recommendation-monthly-legend" aria-label="Chart legend">
      {series.map(item => <li key={item.key}><span aria-hidden="true" data-series={item.key} />{item.label}</li>)}
    </ul>
    <div className="recommendation-monthly-chart" role="group" aria-label="Monthly spending chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={plot} margin={{ top: 12, right: 18, bottom: 1, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#e2e9e1" />
          <XAxis dataKey="month" minTickGap={12} tickFormatter={month => monthLabel(month, false)}
            tickLine={false} tick={{ fontSize: 11, fill: '#435a4d' }} />
          <YAxis width={56} domain={[0, 'auto']} tickFormatter={value => numberFormat.format(value)}
            tickLine={false} tick={{ fontSize: 11, fill: '#435a4d' }} />
          <ReferenceArea x1={handoff ?? forecastStart} x2={forecastEnd} fill="#dcebd6" fillOpacity={0.42} stroke="none" />
          <ReferenceLine x={handoff ?? forecastStart} stroke="#849986" strokeDasharray="3 3" />
          {Array.from(new Set(projection.effective_dates.map(date => date.slice(0, 7))))
            .filter(month => month >= forecastStart && month <= forecastEnd)
            .map(month => <ReferenceLine key={month} x={month} stroke="#b1c9ad" strokeDasharray="2 4" />)}
          <Tooltip content={({ active, label }) => {
            const point = active && points.find(item => item.month === label);
            if (!point) return null;
            return <div className="recommendation-monthly-tooltip" role="status">
              <strong>{monthLabel(point.month)}</strong>
              {series.map(item => {
                const value = point[item.key];
                return value === null ? null : <div key={item.key}>{item.label} · {spending(value)}</div>;
              })}
              {point.current !== null && point.followed !== null &&
                <div>Monthly savings · {spending(point.current - point.followed)}</div>}
            </div>;
          }} />
          {series.map(item => <Line key={item.key} dataKey={item.key} name={item.label} stroke={item.color}
            type={item.key === 'published' ? 'linear' : 'stepAfter'} strokeWidth={item.key === 'current' ? 2 : 2.5}
            strokeDasharray={'dash' in item ? item.dash : undefined}
            dot={item.key === 'published' ? { r: 3, fill: item.color } : false}
            isAnimationActive={false} />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
    <p className="recommendation-impact-note">Estimates use the average of the published months as the current spending rate.</p>
    <p className="recommendation-impact-note">Earliest modeled start {dateLabel.format(new Date(projection.effective_dates[0]))}.
      {projection.conditional && ' Includes savings subject to review.'}
      {projection.covered_scopes < projection.total_scopes &&
        ` Covers ${projection.covered_scopes} of ${projection.total_scopes} supporting scopes.`}
    </p>
  </section>;
}
