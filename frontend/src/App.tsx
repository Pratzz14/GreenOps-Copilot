import { lazy, Suspense, useRef, useState, type KeyboardEvent } from 'react';
import Analysis from './Analysis';

const Silver = lazy(() => import('./Silver'));

const layers = ['Bronze', 'Silver', 'Gold'] as const;
type Layer = (typeof layers)[number];

const placeholders = {
  Gold: {
    title: 'Business insights and decisions.',
    description: 'Gold will contain spending summaries, energy and carbon estimates, and safe savings recommendations.',
  },
};

export default function App() {
  const [layer, setLayer] = useState<Layer>('Bronze');
  const tabs = useRef<HTMLDivElement>(null);

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
    setLayer(layers[next]);
    tabs.current?.querySelectorAll('button')[next]?.focus();
  }

  return (
    <main>
      <header className="app-header">
        <a className="brand" href="#"><span className="brand-mark" aria-hidden="true">G</span>GreenOps <span className="muted">Copilot</span></a>
        <span className="local-badge">LOCAL ANALYSIS</span>
      </header>
      <div className="layer-tabs" role="tablist" aria-label="Data layers" ref={tabs}>
        {layers.map((name, index) => (
          <button key={name} type="button" role="tab" id={`tab-${name}`} aria-controls={`layer-${name}`}
            aria-selected={name === layer} tabIndex={name === layer ? 0 : -1}
            onClick={() => setLayer(name)} onKeyDown={event => navigate(event, index)}>{name}</button>
        ))}
      </div>
      {layers.map(name => (
        <div key={name} id={`layer-${name}`} role="tabpanel" aria-labelledby={`tab-${name}`} hidden={layer !== name} tabIndex={0}>
          {name === 'Bronze' ? <Analysis active={layer === name} /> : name === 'Silver' ? (
            layer === name && <Suspense fallback={<p role="status">Loading Silver…</p>}><Silver /></Suspense>
          ) : (
            <section className="analysis-intro">
              <div>
                <p className="layer-status">Not built yet</p>
                <h1>{placeholders[name].title}</h1>
                <p className="lead">{placeholders[name].description}</p>
              </div>
            </section>
          )}
        </div>
      ))}
      <footer>Sample data ALTYCA, sprintd Basel 2026 · Synthetic usage and volume data · Official baseline Sep 2025 – Aug 2026</footer>
    </main>
  );
}
