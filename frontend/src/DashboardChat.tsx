import { useEffect, useRef, useState, type FormEvent } from 'react';
import { readJson } from './api/analysis';
import { useGold } from './api/gold';
import type { components } from './api/schema';
import { groupLabels, metricLabels, metricValue, monthLabel, sumAvailable, type DashboardFilters } from './dashboardData';
import { Evidence } from './GoldEvidence';

type Models = components['schemas'];
type Turn = { question: string; reply?: Models['Reply']; error?: string };
const path = '/api/v1/dashboard/chat';
const starterQuestions = [
  'Which tools cost the most?',
  'Where is emissions coverage missing?',
  'How did server utilization change week to week?',
];
type ShowDrivers = (scope: Models['Filters'], labels: string[]) => void;

function numeric(value: unknown) {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  return value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
}

function QuerySources({ sources, run, expanded, onShowDrivers }: {
  sources: Models['Source'][]; run: string; expanded?: boolean; onShowDrivers: ShowDrivers;
}) {
  return sources.map((source, index) => {
    const columns = Object.keys(source.rows[0] ?? {});
    const scope = source.ranking_scope;
    const ranking = scope ? source.rows.flatMap(row => {
      const value = scope.metric === 'cost' ? sumAvailable(numeric(row.recorded_cost_chf), numeric(row.imputed_cost_chf))
        : numeric(scope.metric === 'energy' ? row.estimated_kwh : row.reporting_kg_co2e);
      return typeof row.label === 'string' && value !== null ? [{ label: row.label, value }] : [];
    }).slice(0, 3) : [];
    return <div key={index} className="dashboard-chat-result">
      {scope && ranking.length > 0 && <>
        <dl className="dashboard-chat-ranking" aria-label={`Top results · ${metricLabels[scope.metric]}`}>
          {ranking.map(({ label, value }) => <div key={label}>
            <dt>{label}</dt><dd>{metricValue(value, scope.metric, 't CO₂e')}</dd>
          </div>)}
        </dl>
        {scope.group !== 'subject' && <button type="button" className="dashboard-text-button"
          onClick={() => onShowDrivers(scope, ranking.map(row => row.label))}>Show in Biggest drivers</button>}
      </>}
      <details className="dashboard-chat-source" open={expanded || undefined}>
        <summary>{source.layer} · {source.dataset} · {source.scope}</summary>
        <p><a href={source.url}>Open {source.layer} source</a></p>
        {source.evidence_id && <Evidence run={run} id={source.evidence_id} />}
        {source.truncated && <p>Showing the first {source.rows.length} results.</p>}
        {columns.length > 0 && <div tabIndex={0} className="dashboard-chat-table" aria-label="Query results">
          <table className="dashboard-table">
            <thead><tr>{columns.map(column => <th key={column} scope="col">{column.replaceAll('_', ' ')}</th>)}</tr></thead>
            <tbody>{source.rows.map((row, rowIndex) => <tr key={rowIndex}>
              {columns.map(column => <td key={column}>{row[column] == null ? 'Unknown' : String(row[column])}</td>)}
            </tr>)}</tbody>
          </table>
        </div>}
      </details>
    </div>;
  });
}

export default function DashboardChat({ run, filters, onShowDrivers }: {
  run: string; filters: DashboardFilters; onShowDrivers: ShowDrivers;
}) {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState('');
  const [pending, setPending] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const status = useGold<Models['ChatStatus']>('/dashboard/chat/status', open);

  useEffect(() => {
    const history = historyRef.current;
    if (open && history) history.scrollTop = history.scrollHeight;
  }, [open, turns]);

  useEffect(() => {
    if (open) closeRef.current?.focus({ preventScroll: true });
    const overlay = overlayRef.current;
    const viewport = window.visualViewport;
    if (!overlay || !viewport || !open) return;
    function placeOverlay() {
      if (!overlay || !viewport) return;
      overlay.style.setProperty('--chat-viewport-height', `${viewport.height}px`);
      overlay.style.setProperty('--chat-viewport-offset', `${Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)}px`);
    }
    placeOverlay();
    viewport.addEventListener('resize', placeOverlay);
    viewport.addEventListener('scroll', placeOverlay);
    return () => {
      viewport.removeEventListener('resize', placeOverlay);
      viewport.removeEventListener('scroll', placeOverlay);
      overlay.style.removeProperty('--chat-viewport-height');
      overlay.style.removeProperty('--chat-viewport-offset');
    };
  }, [open]);

  function close() {
    setOpen(false);
    launcherRef.current?.focus({ preventScroll: true });
  }

  async function send(message: string, retry = false) {
    if (!message.trim() || pending || !status.data?.configured) return;
    const previous = retry ? turns.slice(0, -1) : turns;
    setTurns([...previous, { question: message }]);
    setQuestion('');
    setPending(true);
    const history = previous.flatMap(turn => turn.reply
      ? [{ question: turn.question, answer: turn.reply.answer,
        scopes: (turn.reply.sources ?? []).map(source => source.scope) }] : []).slice(-4);
    const payload: Models['ChatRequest'] = {
      run_id: run, question: message, history,
      filters: {
        scenario: filters.scenario, group: filters.group, metric: filters.metric, driver: filters.driver,
        months: filters.period?.map(month => month.slice(0, 7)) ?? null,
      },
    };
    try {
      const reply = await readJson<Models['Reply']>(path, 'POST', payload);
      setTurns([...previous, { question: message, reply }]);
    } catch (error) {
      setTurns([...previous, { question: message, error: error instanceof Error ? error.message : 'Chat request failed.' }]);
    } finally {
      setPending(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(question.trim());
  }

  const last = turns.at(-1);
  const period = filters.period === null ? 'All months' : filters.period.length === 0 ? 'No months selected'
    : filters.period.length === 1 ? monthLabel(filters.period[0]) : `${filters.period.length} months selected`;
  return <div ref={overlayRef} className="dashboard-chat-overlay" onKeyDown={event => {
    if (open && event.key === 'Escape') {
      event.stopPropagation();
      close();
    }
  }}>
    <aside id="dashboard-chat" className="dashboard-panel dashboard-chat" aria-labelledby="dashboard-chat-title"
      data-open={open} inert={!open}>
      <header className="dashboard-chat-header">
        <h2 id="dashboard-chat-title">Ask GreenOps</h2>
        <button type="button" ref={closeRef} onClick={close} aria-label="Close chat">×</button>
      </header>
      <p className="dashboard-chat-scope">
        <strong>Dashboard scope</strong> {period} · {filters.scenario} assumptions · {metricLabels[filters.metric]} by {groupLabels[filters.group].toLowerCase()}
        {filters.driver && ` · ${filters.driver}`}
      </p>
      <div ref={historyRef} className="dashboard-chat-body">
        {status.isError ? <p role="alert">Chat status is unavailable.{' '}
          <button type="button" onClick={() => void status.refetch()}>Retry</button></p>
          : !status.data ? <p role="status">Checking AI chat availability…</p>
            : !status.data.configured ? <p>AI chat is unavailable. Configure the backend OpenAI key to enable it.</p>
              : <>
                {turns.length === 0 && <div className="dashboard-chat-starters">
                  <strong>Start with a question</strong>
                  {starterQuestions.map(prompt => <button type="button" key={prompt}
                    onClick={() => void send(prompt)}>{prompt}<span aria-hidden="true">›</span></button>)}
                </div>}
                <div className="dashboard-chat-history" role="log" aria-label="GreenOps conversation" aria-live="polite">
                  {turns.map((turn, index) => <article key={index} className="dashboard-chat-turn">
                    <p className="dashboard-chat-question"><span className="dashboard-visually-hidden">You: </span>{turn.question}</p>
                    {turn.reply && <div className="dashboard-chat-answer">
                      <strong>GreenOps</strong><p>{turn.reply.answer}</p>
                      <QuerySources sources={turn.reply.sources ?? []} run={run} expanded={turn.reply.verified_only}
                        onShowDrivers={(scope, labels) => { close(); onShowDrivers(scope, labels); }} />
                    </div>}
                    {turn.error && <p role="alert">{turn.error}</p>}
                  </article>)}
                  {pending && <p role="status">Checking the published data…</p>}
                </div>
              </>}
      </div>
      {status.data?.configured && !status.isError && <form onSubmit={submit}>
        <label htmlFor="dashboard-chat-question">Your question</label>
        <textarea id="dashboard-chat-question" rows={1} maxLength={2000} value={question}
          enterKeyHint="send"
          placeholder="Which tools cost the most this period?"
          onKeyDown={event => {
            if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
            event.preventDefault();
            if (!event.repeat && !pending && question.trim()) event.currentTarget.form?.requestSubmit();
          }}
          onChange={event => setQuestion(event.target.value)} />
        <button className="dashboard-chat-send" type="submit" disabled={pending || !question.trim()}>Send</button>
        <div className="dashboard-chat-actions">
          {last?.error && <button type="button" disabled={pending}
            onClick={() => void send(last.question, true)}>Retry question</button>}
          <button type="button" disabled={pending || !turns.length} onClick={() => {
            setTurns([]);
            setQuestion('');
          }}>Clear chat</button>
        </div>
      </form>}
    </aside>
    <button className="dashboard-chat-launch" type="button" ref={launcherRef} aria-label="Ask GreenOps"
      aria-controls="dashboard-chat" aria-expanded={open} title="Ask GreenOps"
      onClick={() => open ? close() : setOpen(true)}>
      <span className="dashboard-chat-icon" aria-hidden="true" />
    </button>
  </div>;
}
