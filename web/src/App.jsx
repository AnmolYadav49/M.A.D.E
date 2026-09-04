import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import Shell from './components/Shell.jsx';
import TerminalDrawer from './components/TerminalDrawer.jsx';
import SecurityModal from './components/SecurityModal.jsx';
import ApprovalBar from './components/ApprovalBar.jsx';
import SessionView from './components/SessionView.jsx';
import GraphView from './components/GraphView.jsx';
import RunsView from './components/RunsView.jsx';
import AuditView from './components/AuditView.jsx';
import { useThemeVars, ACCENT_SWATCHES } from './lib/theme.js';
import { usePipeline } from './lib/usePipeline.js';
import { PHASE_META } from './lib/logParser.js';

export default function App() {
  const rootRef = useRef(null);
  const [view, setView] = useState('session');
  const [theme, setTheme] = useState('dark');
  const [accent] = useState(ACCENT_SWATCHES[0]);
  const [termOpen, setTermOpen] = useState(false);
  const [secOpen, setSecOpen] = useState(false);
  const themingTimeout = useRef(null);
  const pipeline = usePipeline();

  useThemeVars(rootRef, theme, accent);

  const toggleTheme = () => {
    const el = rootRef.current;
    if (el) {
      el.classList.add('theming');
      clearTimeout(themingTimeout.current);
      themingTimeout.current = setTimeout(() => el.classList.remove('theming'), 650);
    }
    setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  };

  // Escape closes the terminal drawer / security modal, matching the mockup.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') { setTermOpen(false); setSecOpen(false); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // Entrance animation on mount: nav floats in, hero line rises — ported from the
  // mockup's _initGsap().
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const nav = root.querySelector('[data-nav]');
    if (nav) gsap.from(nav, { y: -70, opacity: 0, duration: 1, ease: 'power4.out' });
    const hero = root.querySelector('[data-hero]');
    if (hero) gsap.from(hero, { y: 34, opacity: 0, duration: 0.9, ease: 'power3.out', delay: 0.12 });
  }, []);

  // Staggered reveal of the active view's [data-reveal] elements, replayed on every
  // tab switch — ported from the mockup's revealActive().
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const sections = [...root.querySelectorAll('main > section')];
    const active = sections.find((s) => getComputedStyle(s).display !== 'none');
    if (!active) return;
    const items = active.querySelectorAll('[data-reveal]');
    if (!items.length) return;
    gsap.killTweensOf(items);
    gsap.fromTo(items, { y: 26, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out', stagger: 0.06, overwrite: true });
  }, [view]);

  // Magnetic pull on Dispatch / Approve buttons — replayed whenever the DOM swaps
  // in a new one (e.g. the idle Dispatch button vs. the HITL Approve button).
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const buttons = root.querySelectorAll('[data-magnetic]');
    const cleanups = [];
    buttons.forEach((btn) => {
      const onMove = (e) => {
        const r = btn.getBoundingClientRect();
        gsap.to(btn, { x: (e.clientX - r.left - r.width / 2) * 0.3, y: (e.clientY - r.top - r.height / 2) * 0.45, duration: 0.4, ease: 'power3.out' });
      };
      const onLeave = () => gsap.to(btn, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1,0.4)' });
      btn.addEventListener('mousemove', onMove);
      btn.addEventListener('mouseleave', onLeave);
      cleanups.push(() => { btn.removeEventListener('mousemove', onMove); btn.removeEventListener('mouseleave', onLeave); });
    });
    return () => cleanups.forEach((fn) => fn());
  }, [view, pipeline.state.phase]);

  const statusMeta = PHASE_META[pipeline.state.phase] || PHASE_META.idle;
  const approvalVisible = view === 'session' && pipeline.state.phase === 'awaiting_hitl';

  return (
    <div
      ref={rootRef}
      style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--fg)', position: 'relative' }}
    >
      <Shell
        view={view}
        setView={setView}
        theme={theme}
        toggleTheme={toggleTheme}
        statusMeta={statusMeta}
        termOpen={termOpen}
        onToggleTerminal={() => setTermOpen((o) => !o)}
        onOpenSecurity={() => setSecOpen(true)}
      />

      <main style={{ marginLeft: 72, padding: '104px 48px 120px', maxWidth: 1320 }}>
        <SessionView visible={view === 'session'} pipeline={pipeline} />
        <GraphView visible={view === 'graph'} />
        <RunsView visible={view === 'runs'} state={pipeline.state} />
        <AuditView visible={view === 'audit'} state={pipeline.state} />
      </main>

      <ApprovalBar visible={approvalVisible} onReject={pipeline.reject} onApprove={pipeline.approve} />
      <TerminalDrawer open={termOpen} onClose={() => setTermOpen(false)} lines={pipeline.state.termLines} />
      <SecurityModal open={secOpen} onClose={() => setSecOpen(false)} />
    </div>
  );
}
