import { lazy, Suspense, useRef, useState, type KeyboardEvent } from 'react';
import Analysis from './Analysis';

const Journey = lazy(() => import('./DataJourney'));
const Workspace = lazy(() => import('./AnalystWorkspace'));
const Silver = lazy(() => import('./Silver'));
const Gold = lazy(() => import('./Gold'));
const Dashboard = lazy(() => import('./Dashboard'));
const Recommendations = lazy(() => import('./Recommendations'));

const layers = ['Data Journey', 'Bronze', 'Silver', 'Gold'] as const;
type Layer = (typeof layers)[number];

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('view');
  const [layer, setLayer] = useState<Layer>(
    layers.find(name => name.toLowerCase() === requested) ?? 'Data Journey',
  );
  const [bronzeVisited, setBronzeVisited] = useState(layer === 'Bronze');
  function selectLayer(next: Layer) {
    setLayer(next);
    if (next === 'Bronze') setBronzeVisited(true);
  }
  const table = params.get('table') ?? '';
  const selection = params.has('view') && table.startsWith(layer.toLowerCase() + ':')
    ? table.slice(layer.length + 1) : undefined;
  const tabs = useRef<HTMLDivElement>(null);
  const path = window.location.pathname;
  const workspace = path === '/analysis';
  const dashboard = path === '/dashboard';
  const recommendations = path === '/recommendations';

  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const last = layers.length - 1;
    let next: number;
    switch (event.key) {
      case 'ArrowLeft': next = index === 0 ? last : index - 1; break;
      case 'ArrowRight': next = index === last ? 0 : index + 1; break;
      case 'Home': next = 0; break;
      case 'End': next = last; break;
      default: return;
    }
    event.preventDefault();
    selectLayer(layers[next]);
    tabs.current?.querySelectorAll('button')[next]?.focus();
  }

  return (
    <>
      <header className={recommendations ? 'app-header recommendations-masthead' : 'app-header'}>
        <a className="brand" href="/dashboard"><span className="brand-mark" aria-hidden="true">G</span>GreenOps Copilot</a>
        <nav className="workspace-navigation" aria-label="Main navigation">
          <a href="/data-explorer" aria-current={workspace || dashboard || recommendations ? undefined : "page"}>Data Explorer</a>
          <a href="/analysis" aria-current={workspace ? "page" : undefined}>Analyst Workspace</a>
          <a href="/dashboard" aria-current={dashboard ? "page" : undefined}>Dashboard</a>
          <a href="/recommendations" aria-current={recommendations ? "page" : undefined}>Recommendations</a>
        </nav>
      </header>
      <main className={dashboard || recommendations ? 'dashboard-shell' : undefined}>
      {recommendations ? <Suspense fallback={<p role="status">Loading Recommendations…</p>}><Recommendations /></Suspense> :
      dashboard ? <Suspense fallback={<p role="status">Loading Dashboard…</p>}><Dashboard /></Suspense> :
      workspace ? <Suspense fallback={<p role="status">Loading Analyst Workspace…</p>}><Workspace /></Suspense> : <>
      <div className="layer-tabs" role="tablist" aria-label="Data layers" ref={tabs}>
        {layers.map((name, index) => (
          <button key={name} type="button" role="tab" id={`tab-${index}`} aria-controls={`layer-${index}`}
            aria-selected={name === layer} tabIndex={name === layer ? 0 : -1}
            onClick={() => selectLayer(name)} onKeyDown={event => navigate(event, index)}>{name}</button>
        ))}
      </div>
      {layers.map((name, index) => (
        <div key={name} id={`layer-${index}`} role="tabpanel" aria-labelledby={`tab-${index}`} hidden={layer !== name} tabIndex={0}>
          {name === 'Data Journey' ? (
            layer === name && <Suspense fallback={<p role="status">Loading Data Journey…</p>}><Journey /></Suspense>
          ) : name === 'Bronze' ? (
            bronzeVisited && <Analysis active={layer === name} initialSource={selection} />
          ) : name === 'Silver' ? (
            layer === name && <Suspense fallback={<p role="status">Loading Silver…</p>}><Silver initialTable={selection} /></Suspense>
          ) : layer === name && <Suspense fallback={<p role="status">Loading Gold…</p>}><Gold initialTable={selection} /></Suspense>}
        </div>
      ))}
      </>}
      <footer>Sample data ALTYCA, sprintd Basel 2026 · Synthetic usage and volume data · Official baseline Sep 2025 – Aug 2026</footer>
      </main>
    </>
  );
}
