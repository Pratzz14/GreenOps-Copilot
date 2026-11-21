import { useState } from 'react';
import { useGold } from './api/gold';
import type { components } from './api/schema';
import { formatCount, numberLocale } from './numberFormat';

type Models = components['schemas'];

function SourceLink({ source }: { source: string }) {
  return source.startsWith('https://')
    ? <a href={source} target="_blank" rel="noreferrer">Source</a>
    : <span>{source}</span>;
}

export function Evidence({ run, id, label = 'View evidence' }: { run: string; id: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const result = useGold<Models['EvidencePage']>(`/runs/${run}/evidence/${id}?offset=${offset}`, open);
  const page = result.data;
  return (
    <details className="gold-evidence" onToggle={event => setOpen(event.currentTarget.open)}>
      <summary>{label}</summary>
      {open && (result.isError ? (
        <div role="alert"><p>{result.error.message}</p><button type="button" onClick={() => void result.refetch()}>Retry</button></div>
      ) : !page ? <p role="status">Loading evidence…</p> : <>
        <ul>{page.items.map((item, index) => (
          <li key={page.offset + index}>
            {item.detail}
            {item.source_file && <small>{item.source_file}{item.source_row === null ? '' : ` · Row ${item.source_row}`}</small>}
            {item.source_record_id && <small><code>{item.source_record_id}</code></small>}
            {item.source_reference && <small><SourceLink source={item.source_reference} /></small>}
          </li>
        ))}</ul>
        {page.total > limit && <div className="pagination">
          <button type="button" disabled={page.offset === 0} onClick={() => setOffset(page.offset - limit)}>Previous</button>
            <span>{formatCount(page.offset + 1)}–{formatCount(page.offset + page.items.length)} of {formatCount(page.total)}</span>
          <button type="button" disabled={page.offset + limit >= page.total}
            onClick={() => setOffset(page.offset + limit)}>Next</button>
        </div>}
      </>)}
    </details>
  );
}

const factorNumber = new Intl.NumberFormat(numberLocale, { maximumFractionDigits: 12 });

export function CalculationFactors({ run, ids }: { run: string; ids?: string[] }) {
  const result = useGold<Models['GoldFactor'][]>(`/runs/${run}/factors`);
  if (result.isError) return (
    <div role="alert"><p>{result.error.message}</p><button type="button" onClick={() => void result.refetch()}>Retry</button></div>
  );
  if (!result.data) return <p role="status">Loading factors…</p>;
  const factors = ids ? result.data.filter(factor => ids.includes(factor.factor_id)) : result.data;
  if (!factors.length) return <p>No factors are published for this selection.</p>;
  return <ul>{factors.map(factor => <li key={factor.factor_id}>
    <strong>{factor.factor_name}</strong>
    <p>{factor.value_mid === null ? factor.value_text ?? 'No compatible numeric factor' :
      `Low / mid / high · ${[factor.value_low, factor.value_mid, factor.value_high].map(value =>
        value === null ? '—' : factorNumber.format(Number(value))).join(' / ')} ${factor.unit}`}</p>
    <p>{factor.definition_and_rationale}</p>
    <small><SourceLink source={factor.source_reference} /></small>
  </li>)}</ul>;
}
