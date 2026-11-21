import type { Dataset, Field, Metric, Rule, Visual } from './api/analysis';

const operations: Record<Rule['op'], string> = {
  eq: 'Equals', in: 'Is one of', contains: 'Contains', lt: 'Less than', lte: 'At most',
  gt: 'Greater than', gte: 'At least', range: 'Between', null: 'Is null', not_null: 'Has a value',
};
const aggregations: Record<Metric['op'], string> = {
  rows: 'Count rows', count: 'Count values', distinct: 'Distinct count', sum: 'Sum', mean: 'Mean',
  min: 'Minimum', max: 'Maximum', median: 'Median', calculate: 'Calculate per row',
};
const numeric = (field?: Field) => field?.type === 'integer' || field?.type === 'decimal';

function FieldSelect({ label, fields, value, onChange, empty }: {
  label: string; fields: Field[]; value: string; onChange: (name: string) => void; empty?: string;
}) {
  return <label>{label}<select value={value} onChange={event => onChange(event.target.value)}>
    {empty && <option value="">{empty}</option>}
    {fields.map(field => <option key={field.name}>{field.name}</option>)}
  </select></label>;
}

function FilterEditor({ rule, fields, update, remove }: {
  rule: Rule; fields: Field[]; update: (next: Rule) => void; remove: () => void;
}) {
  const field = fields.find(item => rule.field === item.name);
  const ordered = numeric(field) || field?.type === 'date';
  const nullable = rule.op === 'null' || rule.op === 'not_null';
  const inputs = rule.op === 'range' ? ['From', 'Through'] : ['Value'];
  const value = rule.values ?? [];
  const kind = field?.type === 'date' ? 'date' : numeric(field) ? 'number' : 'text';

  return <div className="workspace-rule">
    <FieldSelect label="Filter field" value={rule.field} fields={fields}
      onChange={name => update({ field: name, op: 'eq', values: [] })} />
    <label>Operator<select value={rule.op} onChange={event => update({ ...rule, op: event.target.value as Rule['op'], values: [] })}>
      {Object.entries(operations).filter(([key]) => ['eq', 'in', 'null', 'not_null'].includes(key)
        || (key === 'contains' ? !ordered && field?.type !== 'boolean' : ordered))
        .map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </select></label>
    {!nullable && inputs.map((label, index) => <label key={label}>{rule.op === 'in' ? 'Values (one per line)' : label}
      {rule.op === 'in' ? <textarea rows={2} value={value.join('\n')}
        onChange={event => update({ ...rule, values: event.target.value.split('\n') })} />
        : field?.type === 'boolean' ? <select value={value[index] ?? ''} onChange={event => update({ ...rule, values: [event.target.value] })}>
          <option value="">Choose a value</option><option>true</option><option>false</option>
        </select> : <input type={kind} step="any" value={value[index] ?? ''}
          onChange={event => {
            const values = [...value];
            values[index] = event.target.value;
            update({ ...rule, values });
          }} />}
    </label>)}
    <button aria-label="Remove filter" onClick={remove}>Remove</button>
  </div>;
}

export default function VisualBuilder({ dataset, visual, update }: {
  dataset: Dataset; visual: Visual; update: (visual: Visual) => void;
}) {
  const { fields } = dataset;
  const { columns = [], filters = [], groups = [], metrics = [] } = visual;
  const numericFields = fields.filter(numeric);
  const aggregate = groups.length > 0 || metrics.some(metric => metric.op !== 'calculate');
  const output = [
    ...(aggregate ? groups.map(group => group.month ? `${group.field}_month` : group.field)
      : columns.length ? columns : fields.map(field => field.name)),
    ...metrics.map(metric => metric.name).filter(Boolean),
  ];

  return <div className="workspace-builder">
    {!aggregate && <details>
      <summary>Output columns {columns.length ? `· ${columns.length} selected` : '· All fields'}</summary>
      <div className="workspace-field-checks">{fields.map(field => <label key={field.name}>
        <input type="checkbox" checked={columns.includes(field.name)}
          onChange={event => update({ ...visual, columns: event.target.checked
            ? [...columns, field.name] : columns.filter(name => name !== field.name) })} />{field.name}
      </label>)}</div>
    </details>}
    <details>
      <summary>Filters · {filters.length}</summary>
      {filters.map((rule, index) => <FilterEditor key={index} fields={fields} rule={rule}
        update={next => update({ ...visual, filters: filters.map((item, i) => i === index ? next : item) })}
        remove={() => update({ ...visual, filters: filters.filter((_, i) => i !== index) })} />)}
      <button onClick={() => update({ ...visual, filters: [...filters, { field: fields[0].name, op: 'eq', values: [] }] })}>Add filter</button>
    </details>
    <details>
      <summary>Grouping and metrics · {groups.length + metrics.length}</summary>
      {groups.map((group, index) => {
        const change = (field: string, month: boolean) => update({ ...visual, sort: '',
          groups: groups.map((item, i) => i === index ? { field, month } : item) });
        return <div className="workspace-rule" key={index}>
          <FieldSelect label="Group field" value={group.field} fields={fields} onChange={value => change(value, false)} />
          {fields.find(field => field.name === group.field)?.type === 'date' && <label className="workspace-check">
            <input type="checkbox" checked={group.month ?? false} onChange={event => change(group.field, event.target.checked)} />By month
          </label>}
          <button aria-label="Remove grouping" onClick={() => update({ ...visual, sort: '',
            groups: groups.filter((_, i) => i !== index) })}>Remove</button>
        </div>;
      })}
      {metrics.map((metric, index) => {
        const change = (next: Metric) => update({ ...visual, sort: '', metrics: metrics.map((item, i) => i === index ? next : item) });
        const input = ['sum', 'mean', 'min', 'max', 'median'].includes(metric.op) ? numericFields : fields;
        return <div className="workspace-rule" key={index}>
          <label>Metric name<input value={metric.name} onChange={event => change({ ...metric, name: event.target.value })} /></label>
          <label>Calculation<select value={metric.op} onChange={event => {
            const op = event.target.value as Metric['op'];
            change({ ...metric, op, field: ['count', 'distinct'].includes(op) ? fields[0].name : (numericFields[0]?.name ?? ""),
              left: (numericFields[0]?.name ?? ""), right: (numericFields[0]?.name ?? "") });
          }}>{Object.entries(aggregations).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          {metric.op === 'calculate' ? <>
            <FieldSelect label="Left field" fields={numericFields} value={metric.left ?? ''} onChange={left => change({ ...metric, left })} />
            <label>Arithmetic<select value={metric.operator ?? '/'} onChange={event => change({ ...metric, operator: event.target.value as Metric['operator'] })}>
              {['+', '-', '*', '/'].map(op => <option key={op}>{op}</option>)}
            </select></label>
            <FieldSelect label="Right field" fields={numericFields} value={metric.right ?? ''} onChange={right => change({ ...metric, right })} />
          </> : metric.op !== 'rows' && <FieldSelect label="Metric field" fields={input} value={metric.field ?? ''}
            onChange={field => change({ ...metric, field })} />}
          <button aria-label="Remove metric" onClick={() => update({ ...visual, sort: '',
            metrics: metrics.filter((_, i) => i !== index) })}>Remove</button>
        </div>;
      })}
      <div className="workspace-actions">
        <button onClick={() => update({ ...visual, sort: '', groups: [...groups, { field: fields[0].name, month: false }] })}>Add grouping</button>
        <button onClick={() => update({ ...visual, sort: '', metrics: [...metrics, { name: `metric_${metrics.length + 1}`, op: 'rows', field: '', left: '', right: '', operator: '/' }] })}>Add metric</button>
      </div>
    </details>
    <div className="workspace-controls">
      <label>Sort by<select value={visual.sort ?? ''} onChange={event => update({ ...visual, sort: event.target.value })}>
        <option value="">Unsorted</option>{[...new Set(output)].map(name => <option key={name}>{name}</option>)}
      </select></label>
      <label>Direction<select value={visual.descending ? 'desc' : 'asc'}
        onChange={event => update({ ...visual, descending: event.target.value === 'desc' })}>
        <option value="asc">Ascending</option><option value="desc">Descending</option>
      </select></label>
      <label>Row limit<input type="number" min={1} max={10000} value={visual.limit ?? ''} placeholder="Up to 10’000"
        onChange={event => update({ ...visual, limit: event.target.valueAsNumber || null })} /></label>
    </div>
  </div>;
}
