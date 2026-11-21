import { useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react';

export default function DashboardInfo({ label, children }: { label: string; children: ReactNode }) {
  const id = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState(false);
  const [pinned, setPinned] = useState(false);
  const open = preview || pinned;
  useLayoutEffect(() => {
    if (!open) return;
    const button = buttonRef.current!;
    const panel = panelRef.current!;
    const filters = button.closest('.greenops-dashboard')?.querySelector('.dashboard-filters');
    const gutter = 8;

    function positionPanel() {
      const anchor = button.getBoundingClientRect();
      const { clientWidth, clientHeight } = document.documentElement;
      const top = Math.max(gutter, filters?.getBoundingClientRect().bottom ?? 0);
      const belowTop = Math.max(anchor.bottom, top);
      const below = clientHeight - belowTop - gutter;
      const above = anchor.top - top;
      const placeAbove = below < 160 && above > below;
      const left = Math.max(gutter, Math.min(anchor.left, clientWidth - panel.offsetWidth - gutter));

      panel.style.left = `${left}px`;
      panel.style.top = placeAbove ? 'auto' : `${belowTop}px`;
      panel.style.bottom = placeAbove ? `${clientHeight - anchor.top}px` : 'auto';
      panel.style.setProperty('--dashboard-info-space', `${Math.max(0, placeAbove ? above : below)}px`);
    }

    positionPanel();
    window.addEventListener('resize', positionPanel);
    window.addEventListener('scroll', positionPanel);
    return () => {
      window.removeEventListener('resize', positionPanel);
      window.removeEventListener('scroll', positionPanel);
    };
  }, [open]);
  return <div className="dashboard-info" onMouseEnter={() => setPreview(true)}
    onMouseLeave={() => setPreview(false)}
    onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) setPreview(false);
    }}
    onKeyDown={event => {
      if (event.key === 'Escape') {
        buttonRef.current?.focus();
        setPinned(false);
        setPreview(false);
      }
    }}>
    <button ref={buttonRef} aria-label={`About ${label}`} aria-expanded={open} aria-controls={id} type="button"
      className="dashboard-info-button" onFocus={() => setPreview(true)} onClick={() => {
        setPreview(false);
        setPinned(!pinned);
      }}><span aria-hidden="true">i</span></button>
    <div ref={panelRef} id={id} hidden={!open} className="dashboard-info-content">
      {open && children}
    </div>
  </div>;
}
