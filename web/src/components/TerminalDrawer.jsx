import React, { useEffect, useRef } from 'react';

export default function TerminalDrawer({ open, onClose, lines }) {
  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [lines]);

  return (
    <div style={{
      position: 'fixed', left: 72, right: 0, bottom: 0, height: 300, background: 'var(--card)',
      borderTop: '1px solid var(--border)', zIndex: 80, display: 'flex', flexDirection: 'column',
      transform: open ? 'translateY(0)' : 'translateY(112%)',
      transition: 'transform .35s cubic-bezier(.16,1,.3,1)', boxShadow: '0 -12px 40px rgba(0,0,0,.35)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 16px', background: 'var(--fg)', color: 'var(--bg)', fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="mi" style={{ fontSize: 16 }}>terminal</span>Pipeline Terminal</span>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--bg)', cursor: 'pointer', display: 'flex' }}><span className="mi" style={{ fontSize: 18 }}>close</span></button>
      </div>
      <div ref={bodyRef} style={{ flexGrow: 1, overflowY: 'auto', background: '#0D0D0D', fontFamily: "'JetBrains Mono',monospace", fontSize: 12.5, lineHeight: 1.75, padding: 16 }}>
        {lines.map((t, i) => (
          <div key={i} style={{ color: t.c, whiteSpace: 'pre-wrap' }}>{t.text}</div>
        ))}
      </div>
    </div>
  );
}
