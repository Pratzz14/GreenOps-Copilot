import { useState, type ReactNode } from 'react';

type Metric = { label: string; value: string; note?: string };

export function LayerSummary({ label, metrics, children }: {
  label: string;
  metrics: Metric[];
  children?: ReactNode;
}) {
  return <section className="layer-overview" aria-label={label}>
    <dl className="layer-metrics">
      {metrics.map(metric => <div key={metric.label}>
        <dt>{metric.label}</dt>
        <dd>{metric.value}</dd>
        {metric.note && <dd className="metric-note">{metric.note}</dd>}
      </div>)}
    </dl>
    {children}
  </section>;
}

export function LayerDisclosure({ title, description, children }: {
  title: string;
  description: string;
  children: (open: boolean) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [visited, setVisited] = useState(false);

  return <details className="layer-disclosure" onToggle={event => {
    const next = event.currentTarget.open;
    setOpen(next);
    if (next) setVisited(true);
  }}>
    <summary>
      <span><strong>{title}</strong><small>{description}</small></span>
    </summary>
    {visited && <div className="layer-disclosure-body">{children(open)}</div>}
  </details>;
}

export function CatalogRow({ name, records, findings, children }: {
  name: string;
  records: string;
  findings: string;
  children: ReactNode;
}) {
  return <li className="layer-catalog-row">
    <details>
      <summary><strong>{name}</strong><span>{records}</span><span>{findings}</span></summary>
      <div className="layer-catalog-detail">{children}</div>
    </details>
  </li>;
}
