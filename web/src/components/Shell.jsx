import React from 'react';

const VIEWS = [
  { key: 'session', label: 'Session', railIcon: 'dashboard' },
  { key: 'graph', label: 'Graph', railIcon: 'account_tree' },
  { key: 'runs', label: 'Runs', railIcon: 'history' },
  { key: 'audit', label: 'Audit', railIcon: 'shield' },
];

export default function Shell({ view, setView, theme, toggleTheme, statusMeta, termOpen, onToggleTerminal, onOpenSecurity }) {
  return (
    <>
      <aside style={{ position: 'fixed', top: 0, left: 0, bottom: 0, width: 72, background: 'var(--panel)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '18px 0', gap: 6, zIndex: 60 }}>
        <div style={{ width: 40, height: 40, border: '1px solid var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
          <span style={{ fontFamily: "'Bodoni Moda',serif", fontWeight: 700, fontSize: 20, color: 'var(--accent)' }}>M</span>
        </div>
        {VIEWS.map((v) => {
          const active = view === v.key;
          return (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              title={v.label}
              style={{
                width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: active ? 'rgba(176,87,48,.14)' : 'transparent',
                border: 'none', borderLeft: `2px solid ${active ? 'var(--primary)' : 'transparent'}`,
                cursor: 'pointer', transition: 'background .2s',
              }}
            >
              <span className="mi" style={{ fontSize: 22, color: active ? 'var(--accent)' : 'var(--dim3)' }}>{v.railIcon}</span>
            </button>
          );
        })}
        <div style={{ flexGrow: 1 }} />
        <button onClick={onToggleTerminal} title="Pipeline terminal" style={{ width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', background: termOpen ? 'rgba(176,87,48,.14)' : 'transparent', border: 'none', cursor: 'pointer' }}>
          <span className="mi" style={{ fontSize: 22, color: termOpen ? 'var(--accent)' : 'var(--dim3)' }}>terminal</span>
        </button>
        <button onClick={onOpenSecurity} title="Security clearance" style={{ width: 44, height: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent', border: 'none', cursor: 'pointer' }}>
          <span className="mi" style={{ fontSize: 22, color: 'var(--dim3)' }}>security</span>
        </button>
      </aside>

      <nav data-nav="1" style={{ position: 'fixed', top: 16, left: 'calc(72px + (100% - 72px)/2)', transform: 'translateX(-50%)', display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px 8px 20px', background: 'var(--navbg)', backdropFilter: 'blur(16px) saturate(160%)', WebkitBackdropFilter: 'blur(16px) saturate(160%)', border: '1px solid var(--navborder)', borderRadius: 999, boxShadow: '0 8px 32px rgba(0,0,0,.35)', zIndex: 55, maxWidth: 'min(880px, calc(100% - 104px))' }}>
        <span style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 16, fontWeight: 600, letterSpacing: '.04em', paddingRight: 14, borderRight: '1px solid var(--border)' }}>M.A.D.E.</span>
        <div style={{ display: 'flex', gap: 2 }}>
          {VIEWS.map((v) => {
            const active = view === v.key;
            return (
              <button
                key={v.key}
                onClick={() => setView(v.key)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px 12px', fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: active ? 'var(--fg)' : 'var(--dim3)', borderBottom: `2px solid ${active ? 'var(--fg)' : 'transparent'}` }}
              >
                {v.label}
              </button>
            );
          })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 12, borderLeft: '1px solid var(--border)' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: statusMeta.color, display: 'inline-block', animation: statusMeta.anim }} />
          <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim1)', minWidth: 112 }}>{statusMeta.status}</span>
        </div>
        <button onClick={toggleTheme} title="Toggle theme" aria-label="Toggle theme" style={{ position: 'relative', width: 56, height: 28, borderRadius: 999, border: '1px solid var(--navborder)', background: theme === 'light' ? 'rgba(176,87,48,.18)' : 'rgba(255,255,255,.08)', cursor: 'pointer', transition: 'background .5s ease', flexShrink: 0, marginLeft: 4, padding: 0 }}>
          <span style={{ position: 'absolute', top: 2, left: 2, width: 22, height: 22, borderRadius: '50%', background: 'var(--fg)', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: theme === 'light' ? 'translateX(28px)' : 'translateX(0)', transition: 'transform .55s cubic-bezier(.34,1.56,.64,1), background .5s ease', boxShadow: '0 2px 6px rgba(0,0,0,.35)' }}>
            <span className="mi" style={{ fontSize: 14, color: 'var(--bg)', transition: 'color .5s ease' }}>{theme === 'light' ? 'light_mode' : 'dark_mode'}</span>
          </span>
        </button>
      </nav>
    </>
  );
}

export { VIEWS };
