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

export function LayerDisclosure({ title, description, children, defaultOpen = false }: {
  title: string;
  description: string;
  children: (open: boolean) => ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [visited, setVisited] = useState(defaultOpen);

  return <details className="layer-disclosure" open={open} onToggle={event => {
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

export function CatalogRow({ name, records, findings, children, defaultOpen = false }: {
  name: string;
  records: string;
  findings?: string;
  defaultOpen?: boolean;
  children: ReactNode | (() => ReactNode);
}) {
  const [open, setOpen] = useState(defaultOpen);
  const lazy = typeof children === 'function';
  return <li className={findings === undefined ? 'layer-catalog-row layer-catalog-row-simple' : 'layer-catalog-row'}>
    <details open={lazy ? open : undefined} onToggle={lazy ? event => setOpen(event.currentTarget.open) : undefined}>
      <summary><strong>{name}</strong><span>{records}</span>{findings !== undefined ? <span>{findings}</span> : null}</summary>
      {lazy ? open && <div className="layer-catalog-detail">{children()}</div> :
        <div className="layer-catalog-detail">{children}</div>}
    </details>
  </li>;
}
