import { useQuery } from '@tanstack/react-query';
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts';
import { analysis, type Chart, type Field, type Result } from './api/analysis';
import { formatCount, formatExactNumber, isNumericColumn } from './numberFormat';

const numeric = (field?: Field) => field && isNumericColumn(field.type);

function histogram(values: number[]) {
  const low = Math.min(...values);
  const high = Math.max(...values);
  const count = low === high ? 1 : 8;
  const width = count === 1 ? 1 : (high - low) / count;
  const bins = Array.from({ length: count }, (_, index) => ({
    x: count === 1 ? String(low) : `${(low + index * width).toPrecision(4)}–${(low + (index + 1) * width).toPrecision(4)}`,
    y: 0,
  }));
  values.forEach(value => bins[Math.min(count - 1, Math.floor((value - low) / width))].y++);
  return bins;
}

export default function ResultChart({ result, chart, update }: {
  result: Result; chart: Chart; update: (chart: Chart) => void;
}) {
  const { metadata } = result;
  const fields = metadata.fields;
  const kind = chart.kind ?? 'bar';
  const x = fields.findIndex(field => field.name === chart.x);
  const y = fields.findIndex(field => field.name === chart.y);
  const measure = kind === 'histogram' ? x : y;
  const valid = x >= 0 && !!numeric(fields[measure]) && (kind !== 'scatter' || !!numeric(fields[x]));
  const query = useQuery({
    queryKey: ['analysis-chart', metadata.id],
    queryFn: () => analysis<Result>(`/results/${metadata.id}?limit=1000`),
    enabled: valid && metadata.row_count > 0 && metadata.row_count <= 1000,
    staleTime: Infinity,
  });
  const rows = query.data?.rows ?? [];
  const compatible = [measure, ...(kind === 'scatter' ? [x] : [])].every(index => {
    const key = fields[index]?.unit_key;
    if (!key) return true;
    const column = fields.findIndex(field => field.name === key);
    const values = new Set(rows.filter(row => row[index] != null).map(row => row[column]));
    return column >= 0 && values.size <= 1 && !values.has(null);
  });
  const observations = rows.filter(row => row[x] != null && row[measure] != null
    && Number.isFinite(Number(row[measure])) && (kind !== 'scatter' || Number.isFinite(Number(row[x]))));
  const points = !observations.length ? [] : kind === 'histogram'
    ? histogram(observations.map(row => Number(row[x])))
    : observations.map(row => ({ x: kind === 'scatter' ? Number(row[x]) : String(row[x]), y: Number(row[y]) }));

  return <div>
    <div className="workspace-controls">
      <label>Chart type<select value={kind} onChange={event => update({ ...chart, kind: event.target.value as Chart['kind'] })}>
        <option value="bar">Bar</option><option value="line">Line</option><option value="scatter">Scatter</option>
        <option value="histogram">Histogram</option>
      </select></label>
      <label>{kind === 'histogram' ? 'Distribution field' : 'Horizontal axis'}<select value={x < 0 ? '' : chart.x}
        onChange={event => update({ ...chart, x: event.target.value })}>
        <option value="">Choose a field</option>{fields.filter(field => !['scatter', 'histogram'].includes(kind) || numeric(field))
          .map(field => <option key={field.name}>{field.name}</option>)}
      </select></label>
      {kind !== 'histogram' && <label>Vertical axis<select value={y < 0 ? '' : chart.y}
        onChange={event => update({ ...chart, y: event.target.value })}>
        <option value="">Choose a measure</option>{fields.filter(numeric).map(field => <option key={field.name}>{field.name}</option>)}
      </select></label>}
    </div>
    {metadata.row_count > 1000 ? <p>Filter or aggregate further to chart at most {formatCount(1000)} returned rows.</p>
      : !valid ? <p>Choose compatible chart fields.</p>
      : query.isError ? <p role="alert">{query.error.message}</p>
      : query.isFetching ? <p role="status">Loading chart population…</p>
      : !compatible ? <p>Include the corresponding unit field and filter to a single compatible unit.</p>
      : !points.length ? <p>No plottable observations.</p>
      : <>
        <p className="scope-note">{formatCount(observations.length)} plotted observations from {formatCount(metadata.row_count)}
          {' '}returned rows · {metadata.truncated || metadata.requested_limit ? 'Limited query result' : 'Complete query result'}
          {' '}· {fields[measure].unit ?? 'Unit unspecified'}</p>
        <div className="workspace-chart" role="img" aria-label={`${kind} chart of ${fields[measure].name}`}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={points} margin={{ top: 12, right: 24, bottom: 12, left: 12 }}>
              <CartesianGrid stroke="#e0e5dc" /><XAxis dataKey="x" type={kind === 'scatter' ? 'number' : 'category'}
                tickFormatter={numeric(fields[x]) ? formatExactNumber : undefined} />
              <YAxis type="number" label={kind === 'histogram' ? 'Count' : undefined} tickFormatter={formatExactNumber} />
              <Tooltip formatter={value => typeof value === 'number' ? formatExactNumber(value) : value} />
              {kind === 'line' ? <Line dataKey="y" name={fields[measure].name} stroke="#315e46" isAnimationActive={false} />
                : kind === 'scatter' ? <Scatter dataKey="y" name={fields[measure].name} fill="#315e46" isAnimationActive={false} />
                : <Bar dataKey="y" name={kind === 'histogram' ? 'Count' : fields[measure].name} fill="#52875e" isAnimationActive={false} />}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </>}
  </div>;
}
