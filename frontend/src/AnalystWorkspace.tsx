import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { analysis, type Catalog, type Dataset, type Definition, type Draft, type Result, type Saved, type Scope } from './api/analysis';
import AnalysisResults from './AnalysisResults';
import VisualBuilder from './VisualBuilder';

const emptyVisual = { sort: '', descending: false };
const emptyChart = { kind: 'bar', x: '', y: '' } as const;
const savedKey = ['analysis-saved'];
const queryDefinition = ({ version, dataset, filters, mode, sql, visual }: Definition) =>
  JSON.stringify({ version, dataset, filters, mode, ...(mode === 'sql' ? { sql } : { visual }) });
const exampleSql = (dataset: string) => `SELECT *\nFROM "${dataset}"\nLIMIT 100`;
const freshDefinition = (catalog: Catalog, dataset = 'cost_facts'): Definition => ({
  version: catalog.version, dataset, filters: catalog.defaults, mode: 'sql', visual: emptyVisual, sql: exampleSql(dataset), chart: emptyChart,
});

function Fields({ dataset }: { dataset: Dataset }) {
  const [search, setSearch] = useState('');
  const fields = dataset.fields.filter(field => field.name.toLowerCase().includes(search.toLowerCase()));
  return <>
    <label>Find fields<input type="search" placeholder="Search this dataset" value={search}
      onChange={event => setSearch(event.target.value)} /></label>
    <ul className="workspace-fields">
      {fields.map(field => <li key={field.name}><code>{field.name}</code><small>
        {field.type}{field.unit ? ` · ${field.unit}` : ''}{field.unit_key ? ` · by ${field.unit_key}` : ''}
      </small></li>)}
      {!fields.length && <li>No matching fields</li>}
    </ul>
  </>;
}

function Workspace({ catalog }: { catalog: Catalog }) {
  const [definition, setDefinition] = useState(() => freshDefinition(catalog));
  const [result, setResult] = useState<{ page: Result; definition: string }>();
  const [preview, setPreview] = useState<{ sql: string; definition: string }>();
  const [savedId, setSavedId] = useState('');
  const [name, setName] = useState('');
  const [notice, setNotice] = useState('');
  const [question, setQuestion] = useState('');
  const queryClient = useQueryClient();
  const saved = useQuery({ queryKey: savedKey, queryFn: () => analysis<Saved[]>('/saved') });
  const run = useMutation({
    mutationFn: (value: Definition) => analysis<Result>('/query', 'POST', value),
    onSuccess: (page, value) => {
      setResult({ page, definition: queryDefinition(value) });
      if (value.mode === 'visual') setPreview({ sql: page.metadata.sql, definition: queryDefinition(value) });
    },
  });
  const generate = useMutation({
    mutationFn: (value: { definition: Definition; open: boolean }) =>
      analysis<{ sql: string }>('/preview', 'POST', value.definition),
    onSuccess: ({ sql }, value) => {
      setPreview({ sql, definition: queryDefinition(value.definition) });
      if (value.open) setDefinition({ ...value.definition, mode: 'sql', sql });
    },
  });
  const draft = useMutation({
    mutationFn: () => analysis<Draft>('/draft', 'POST', {
      version: definition.version, filters: definition.filters ?? catalog.defaults,
      question: question.trim(),
    }),
    onSuccess: ({ dataset, sql }) => {
      if (dataset && sql) setDefinition(value => ({
        ...value, dataset, mode: 'sql', sql, chart: dataset === value.dataset ? value.chart : emptyChart,
      }));
      run.reset();
      generate.reset();
    },
  });
  const save = useMutation({
    mutationFn: () => analysis<Saved>(savedId ? `/saved/${savedId}` : '/saved', savedId ? 'PUT' : 'POST',
      { name: name.trim(), definition }),
    onSuccess: entry => {
      setSavedId(entry.id);
      setNotice(`Saved ${entry.name}`);
      void queryClient.invalidateQueries({ queryKey: savedKey });
    },
  });
  const remove = useMutation({
    mutationFn: () => analysis<void>(`/saved/${savedId}`, 'DELETE'),
    onSuccess: () => {
      setSavedId('');
      setName('');
      setNotice('Saved definition deleted');
      void queryClient.invalidateQueries({ queryKey: savedKey });
    },
  });
  const dataset = catalog.datasets.find(item => item.name === definition.dataset);
  const rebase = definition.version !== catalog.version;
  const busy = run.isPending || generate.isPending || draft.isPending || save.isPending || remove.isPending;
  const key = queryDefinition(definition);
  const currentSql = preview?.definition === key ? preview.sql : '';
  const error = run.error ?? generate.error ?? save.error ?? remove.error ?? saved.error;
  const filters = definition.filters ?? catalog.defaults;

  const canRun = !busy && !rebase && !!dataset && !dataset.unavailable
    && (definition.mode === 'visual' || !!definition.sql?.trim());

  function runQuery() {
    if (!canRun) return;
    generate.reset();
    run.mutate(definition);
  }

  function change(next: Definition) {
    run.reset();
    generate.reset();
    draft.reset();
    save.reset();
    remove.reset();
    setNotice('');
    setDefinition(next);
  }

  function scope<Key extends keyof Scope>(field: Key, value: Scope[Key]) {
    change({ ...definition, filters: { ...filters, [field]: value } });
  }

  function open(id: string) {
    const entry = saved.data?.find(item => item.id === id);
    setSavedId(id);
    setName(entry?.name ?? '');
    change(entry?.definition ?? freshDefinition(catalog));
  }

  return <>
    <div className="workspace-grid">
      <aside className="panel workspace-catalog" aria-label="Dataset and field catalog">
        <h2>Dataset fields</h2>
        <p className="workspace-schema-name"><code>{definition.dataset}</code></p>
        {dataset && <>
          <p>{dataset.purpose}</p><p className="scope-note"><strong>Grain</strong> · {dataset.grain}</p>
          <Fields key={dataset.name} dataset={dataset} />
          <details className="workspace-evidence"><summary>Dataset limitations and inputs</summary>
            <p>{dataset.date_context}</p><p>{dataset.inputs.join(' · ')}</p><ul>{dataset.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul>
          </details>
        </>}
      </aside>
      <section className="panel workspace-editor" aria-label="Configure analysis">
        <div className="workspace-results-heading">
          <h2>Query editor</h2>
          <div className="workspace-actions workspace-editor-modes">
            <div className="segmented workspace-modes">
              <button aria-pressed={definition.mode === 'sql'} disabled={busy}
                onClick={() => change({ ...definition, mode: 'sql', sql: definition.sql || currentSql || exampleSql(definition.dataset) })}>SQL</button>
              <button aria-pressed={definition.mode === 'visual'} disabled={busy}
                onClick={() => change({ ...definition, mode: 'visual' })}>Visual</button>
            </div>
          </div>
        </div>
        <fieldset disabled={busy}>
          <div className="workspace-controls workspace-dataset-tools">
            <label>Dataset<select aria-label="Dataset" value={definition.dataset} disabled={busy} onChange={event => change({
              ...freshDefinition(catalog, event.target.value), version: definition.version, filters, mode: definition.mode,
            })}>
              {catalog.datasets.some(item => item.name === definition.dataset) ? null : <option>{definition.dataset}</option>}
              {(['source', 'connected', 'prepared'] as const).map(kind => <optgroup key={kind} label={{
                source: 'Cleaned sources', connected: 'Connected tables', prepared: 'Verified joins',
              }[kind]}>
                {catalog.datasets.filter(item => item.kind === kind).map(item => <option key={item.name} value={item.name}>
                  {item.name}{item.unavailable ? ' (unavailable)' : ''}
                </option>)}
              </optgroup>)}
            </select></label>
            <label>Starter investigation<select value="" onChange={event => {
              const starter = catalog.starters[Number(event.target.value)];
              if (event.target.value !== '' && starter) {
                change({ ...freshDefinition(catalog, starter.dataset), version: definition.version, filters, mode: 'sql', sql: starter.sql });
              }
            }}>
              <option value="">Choose a starter</option>{catalog.starters.map((starter, index) =>
                <option key={starter.name} value={index}>{starter.name}</option>)}
            </select></label>
          </div>
          <details className="workspace-query-scope">
            <summary>Scope <span>{filters.period} · {filters.disposition} · {filters.financial === 'eligible' ? 'eligible costs' : 'all recorded versions'}</span></summary>
            <div className="workspace-controls">
              <label>Period<select value={filters.period} onChange={event => scope('period', event.target.value as Scope['period'])}>
                <option value="baseline">Baseline</option><option value="full">Full history</option>
              </select></label>
              <label>Disposition<select value={filters.disposition} onChange={event => scope('disposition', event.target.value as Scope['disposition'])}>
                <option value="accepted">Accepted</option><option value="review">Review</option><option value="duplicate">Duplicate</option>
                <option value="quarantined">Quarantined</option><option value="all">All dispositions</option>
              </select></label>
              <label>Financial eligibility<select value={filters.financial} onChange={event => scope('financial', event.target.value as Scope['financial'])}>
                <option value="eligible">Eligible baseline costs</option><option value="all">All recorded versions</option>
              </select></label>
            </div>
            <p className="workspace-hint">Baseline {catalog.baseline_start} to {catalog.baseline_end}. Financial eligibility masks excluded amounts and retains coverage rows.</p>
          </details>
          <section className="workspace-ask" aria-label="Draft SQL from a question">
            <label>Ask a question
              <textarea value={question} rows={3} maxLength={2000}
                placeholder="What was the recorded CHF spend by department?"
                onChange={event => { draft.reset(); setQuestion(event.target.value); }} />
            </label>
            <div className="workspace-actions">
              <button type="button" className="workspace-primary" disabled={!catalog.ai_configured || !question.trim() || rebase}
                onClick={() => draft.mutate()}>{draft.isPending ? 'Drafting SQL…' : 'Draft SQL'}</button>
              <span className="workspace-hint">AI chooses a Silver dataset and uses your current scope.</span>
            </div>
            {!catalog.ai_configured && <p className="scope-note">
              Add <code>OPENAI_API_KEY</code> to the project’s <code>.env</code> file, then reload.
            </p>}
            {draft.error && <p className="error-panel" role="alert">{draft.error.message}</p>}
            {draft.data && <p role="status">{draft.data.sql ? `Dataset: ${draft.data.dataset}. Review the draft before running. ` : ''}{draft.data.explanation}</p>}
          </section>
          {dataset?.unavailable && <p className="error-panel" role="alert">{dataset.unavailable}</p>}
          {definition.mode === 'visual' ? dataset && <VisualBuilder dataset={dataset} visual={definition.visual ?? emptyVisual}
            update={visual => change({ ...definition, visual })} /> : <label className="workspace-sql-label">Read-only SQL
              <textarea className="workspace-sql" spellCheck={false} rows={10} value={definition.sql ?? ''}
                onChange={event => change({ ...definition, sql: event.target.value })}
                onKeyDown={event => {
                  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                    event.preventDefault();
                    runQuery();
                  }
                }} />
              <span className="workspace-hint">Use one SELECT over the chosen dataset. Calculated SQL units may require verification.</span>
            </label>}
          {rebase && <div className="workspace-stale" role="status">
            <p>This definition uses Silver <code>{definition.version}</code>. Current Silver is <code>{catalog.version}</code>.</p>
            <button onClick={() => change({ ...definition, version: catalog.version })}>Confirm rebase to current Silver</button>
          </div>}
          <div className="workspace-actions workspace-run">
            <button className="workspace-primary" disabled={!canRun}
              onClick={runQuery}>{run.isPending ? 'Running…' : 'Run analysis'}</button>
            {definition.mode === 'sql' && <span className="workspace-hint workspace-shortcut">Ctrl or ⌘ + Enter</span>}
            {definition.mode === 'visual' && <>
              <button disabled={rebase || !dataset || !!dataset.unavailable}
                onClick={() => { run.reset(); generate.mutate({ definition, open: false }); }}>Show generated SQL</button>
              <button disabled={rebase || !dataset || !!dataset.unavailable}
                onClick={() => { run.reset(); generate.mutate({ definition, open: true }); }}>Open in SQL</button>
            </>}
          </div>
          {definition.mode === 'visual' && currentSql && <pre aria-label="Generated SQL">{currentSql}</pre>}
          <details className="workspace-evidence">
            <summary>Saved analyses</summary>
            <div className="workspace-controls">
              <label>Open saved analysis<select value={savedId} onChange={event => open(event.target.value)}>
                <option value="">New analysis</option>{saved.data?.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select></label>
              <label>Analysis name<input value={name} maxLength={120} onChange={event => setName(event.target.value)} /></label>
            </div>
            <div className="workspace-actions">
              <button disabled={!name.trim()} onClick={() => save.mutate()}>{savedId ? 'Update definition' : 'Save definition'}</button>
              {savedId && <button onClick={() => {
                if (window.confirm('Delete this saved analysis definition?')) remove.mutate();
              }}>Delete definition</button>}
            </div>
            {notice && <p role="status">{notice}</p>}
          </details>
        </fieldset>
        {error && <p className="error-panel" role="alert">{error.message}</p>}
      </section>
    </div>
    {result && <AnalysisResults key={result.page.metadata.id} initial={result.page} stale={result.definition !== key}
      chart={definition.chart ?? emptyChart} onChart={chart => setDefinition({ ...definition, chart })} />}
  </>;
}

export default function AnalystWorkspace() {
  const query = useQuery({ queryKey: ['analysis-catalog'], queryFn: () => analysis<Catalog>('/catalog') });
  return <div className="analyst-workspace">
    <section className="analysis-intro">
      <div><h1>Analyst Workspace</h1><p className="lead">Write SQL or draft a query from a question.</p></div>
    </section>
    {query.data ? <Workspace catalog={query.data} /> : <p className={query.isError ? 'error-panel' : 'loading'}
      role={query.isError ? 'alert' : 'status'}>{query.error?.message ?? 'Loading the Silver catalog…'}</p>}
  </div>;
}
