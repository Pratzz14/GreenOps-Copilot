import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, readJson } from './api/analysis';
import { useGold } from './api/gold';
import type { components } from './api/schema';
import { groupLabels, metricLabels, metricValue, monthLabel, sumAvailable, type DashboardFilters } from './dashboardData';
import { Evidence } from './GoldEvidence';
import { useDashboardVoice } from './useDashboardVoice';

type Models = components['schemas'];
type Turn = { question: string; spoken: boolean; reply?: Models['Reply']; error?: string };
const path = '/api/v1/dashboard/chat';
const starterQuestions = [
  'Which tools cost the most?',
  'Where is emissions coverage missing?',
  'How did server utilization change week to week?',
];
type ShowDrivers = (scope: Models['Filters'], labels: string[]) => void;
type Voice = ReturnType<typeof useDashboardVoice>;

const voiceLabels = {
  starting: 'Opening microphone…',
  listening: 'Listening',
  transcribing: 'Transcribing',
  'getting-answer': 'Getting answer',
  preparing: 'Preparing audio…',
  speaking: 'Speaking',
};
const voiceIssues = {
  'autoplay-blocked': ['Tap to play the answer.', 'Play answer'],
  'microphone-error': ['Microphone access is unavailable.', 'Try again'],
  'too-long': ['Try a shorter question.', 'Try again'],
  'transcription-error': ['We couldn’t transcribe your recording.', 'Retry transcription'],
  'playback-error': ['We couldn’t play this answer.', 'Retry playback'],
  'empty-transcript': ['No speech was transcribed. Try again.', 'Try again'],
};

function VoiceIcon({ audio = false }: { audio?: boolean }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {audio
      ? <path d="M3 9v6h4l5 4V5L7 9H3zm13 0a4 4 0 0 1 0 6m2-9a8 8 0 0 1 0 12" />
      : <><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-3 0h6" /></>}
  </svg>;
}

function VoiceControls({ voice, pending, typeInstead }: { voice: Voice; pending: boolean; typeInstead: () => void }) {
  if (voice.phase === 'idle') {
    return <div className="dashboard-voice-bar">
      <button type="button" className="dashboard-voice-primary" onClick={() => void voice.start()} disabled={pending}>
        <VoiceIcon /> Start voice
      </button>
    </div>;
  }
  const phase = voice.phase;
  if (phase in voiceIssues) {
    const [message, retry] = voiceIssues[phase as keyof typeof voiceIssues];
    return <div className="dashboard-voice-bar dashboard-voice-problem">
      <p role="alert">{voice.message ?? message}</p>
      <div className="dashboard-voice-actions">
        <button type="button" className="dashboard-voice-primary" onClick={voice.retry}>{retry}</button>
        {voice.handsFree || phase === 'microphone-error'
          ? <button type="button" onClick={typeInstead}>Type instead</button>
          : <button type="button" onClick={voice.end}>Dismiss</button>}
        {voice.handsFree && <button type="button" onClick={voice.end}>End voice</button>}
      </div>
    </div>;
  }
  const speaking = phase === 'speaking';
  return <div className="dashboard-voice-bar">
    <div className="dashboard-voice-state">
      {(phase === 'listening' || speaking) && <VoiceIcon audio={speaking} />}
      <div role="status">
        <strong>{voiceLabels[phase as keyof typeof voiceLabels]}</strong>
        {speaking && <small>AI-generated audio</small>}
      </div>
      <div className="dashboard-voice-actions">
        {speaking && voice.handsFree && <button type="button" onClick={voice.interrupt}>Interrupt</button>}
        <button type="button" onClick={voice.end}>{voice.handsFree ? 'End voice' : 'Stop audio'}</button>
      </div>
    </div>
  </div>;
}

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
  const requestRef = useRef<AbortController | null>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const queryClient = useQueryClient();
  const status = useGold<Models['ChatStatus']>('/dashboard/chat/status', open);
  const voice = useDashboardVoice(message => send(message, false, true));
  // The parent keys the dashboard by run ID and disposes the chat when this query changes.
  useGold<Models['GoldRun']>('/runs/current', voice.handsFree || voice.busy, 3000);
  const canUseVoice = Boolean(status.data?.voice_configured);
  const canSend = !pending && !voice.busy;

  const cancelRequest = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
  }, []);
  useLayoutEffect(() => cancelRequest, [cancelRequest]);

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
    voice.end();
    setOpen(false);
    launcherRef.current?.focus({ preventScroll: true });
  }

  async function send(message: string, retry = false, spoken = false) {
    if (!message.trim() || requestRef.current || !status.data?.configured) return;
    const previous = retry ? turns.slice(0, -1) : turns;
    const turn = { question: message, spoken };
    const request = new AbortController();
    requestRef.current = request;
    setTurns([...previous, turn]);
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
      const reply = await readJson<Models['Reply']>(path, 'POST', payload, request.signal);
      if (requestRef.current !== request) return;
      setTurns([...previous, { ...turn, reply }]);
      return reply;
    } catch (error) {
      if (requestRef.current !== request) return;
      if (error instanceof ApiError && error.status === 409) {
        voice.end();
        void queryClient.invalidateQueries({ queryKey: ['gold', '/runs/current'] });
      }
      setTurns([...previous, { ...turn, error: error instanceof Error ? error.message : 'Chat request failed.' }]);
    } finally {
      if (requestRef.current === request) {
        requestRef.current = null;
        setPending(false);
      }
    }
  }

  function sendQuietly(message: string, retry = false) {
    if (canSend && message) void voice.runQuietly(() => send(message, retry));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendQuietly(question.trim());
  }

  function clear() {
    voice.end();
    cancelRequest();
    setPending(false);
    setTurns([]);
    setQuestion('');
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
                  {starterQuestions.map(prompt => <button type="button" key={prompt} disabled={!canSend}
                    onClick={() => sendQuietly(prompt)}>{prompt}<span aria-hidden="true">›</span></button>)}
                </div>}
                <div className="dashboard-chat-history" role="log" aria-label="GreenOps conversation" aria-live="polite">
                  {turns.map((turn, index) => <article key={index} className="dashboard-chat-turn">
                    <p className="dashboard-chat-question">
                      <span className="dashboard-visually-hidden">{turn.spoken ? 'Spoken question: ' : 'You: '}</span>
                      {turn.question}
                    </p>
                    {turn.reply && <div className="dashboard-chat-answer">
                      <strong>GreenOps</strong><p>{turn.reply.answer}</p>
                      <QuerySources sources={turn.reply.sources ?? []} run={run} expanded={turn.reply.verified_only}
                        onShowDrivers={(scope, labels) => { close(); onShowDrivers(scope, labels); }} />
                      {canUseVoice && !turn.spoken && <button type="button" className="dashboard-chat-listen"
                        disabled={pending || (voice.phase !== 'idle' && voice.phase !== 'listening')}
                        onClick={() => { if (turn.reply) voice.listen(turn.reply.answer); }}>
                        <VoiceIcon audio /> Listen
                      </button>}
                    </div>}
                    {turn.error && <p role="alert">{turn.error}</p>}
                  </article>)}
                  {pending && voice.phase !== 'getting-answer' && <p role="status">Checking the published data…</p>}
                </div>
              </>}
      </div>
      {(voice.phase !== 'idle' || (status.data?.configured && !status.isError && canUseVoice)) &&
        <VoiceControls voice={voice} pending={pending}
        typeInstead={() => { voice.end(); composerRef.current?.focus(); }} />}
      {status.data?.configured && !status.isError && <form onSubmit={submit}>
        <label htmlFor="dashboard-chat-question">Your question</label>
        <textarea ref={composerRef} id="dashboard-chat-question" rows={1} maxLength={2000} value={question}
          enterKeyHint="send"
          placeholder="Which tools cost the most this period?"
          onKeyDown={event => {
            if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
            event.preventDefault();
            if (!event.repeat && canSend && question.trim()) event.currentTarget.form?.requestSubmit();
          }}
          onChange={event => setQuestion(event.target.value)} />
        <button className="dashboard-chat-send" type="submit" disabled={!canSend || !question.trim()}>Send</button>
        <div className="dashboard-chat-actions">
          {last?.error && <button type="button" disabled={!canSend}
            onClick={() => sendQuietly(last.question, true)}>Retry question</button>}
          <button type="button" disabled={!turns.length && voice.phase === 'idle'} onClick={clear}>Clear chat</button>
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
