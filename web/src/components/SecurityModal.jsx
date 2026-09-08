import React, { useState } from 'react';

export default function SecurityModal({ open, onClose }) {
  const [strict, setStrict] = useState(true);

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
          zIndex: 90, opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none', transition: 'opacity .3s ease',
        }}
      />
      <div style={{
        position: 'fixed', top: '50%', left: '50%', width: '90%', maxWidth: 480, background: 'var(--card)',
        border: '1px solid var(--border)', zIndex: 95, padding: 26, display: 'flex', flexDirection: 'column', gap: 20,
        opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none',
        transform: `translate(-50%,-50%) ${open ? 'scale(1)' : 'scale(0.95)'}`,
        transition: 'opacity .3s ease, transform .35s cubic-bezier(.16,1,.3,1)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: 14 }}>
          <h3 style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 22, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="mi" style={{ fontSize: 22, color: 'var(--accent)' }}>security</span>Security Clearance
          </h3>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--dim3)', cursor: 'pointer', display: 'flex' }}>
            <span className="mi" style={{ fontSize: 20 }}>close</span>
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: "'JetBrains Mono',monospace", fontSize: 12.5, lineHeight: 1.6 }}>
          <div>
            <div style={{ color: 'var(--dim3)', textTransform: 'uppercase', letterSpacing: '.06em', fontSize: 10, marginBottom: 6 }}>AST Rules</div>
            <div style={{ color: 'var(--ok)' }}>✓ Whitelist · numpy, pandas, langchain, faiss</div>
            <div style={{ color: 'var(--err)' }}>✕ Blocked · subprocess, eval, exec, os.system</div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            <span style={{ color: 'var(--dim2)' }}>Sandbox</span><span style={{ color: 'var(--fg)' }}>Isolated subprocess · 10–15s timeout</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--dim2)' }}>Human-in-the-loop</span><span style={{ color: 'var(--fg)' }}>Required before execution</span>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: 16 }}>
          <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--dim2)' }}>Strict AST Enforcement</span>
          <span
            onClick={() => setStrict((v) => !v)}
            style={{ position: 'relative', width: 42, height: 22, borderRadius: 999, background: strict ? 'var(--primary)' : 'var(--border)', display: 'inline-block', cursor: 'pointer', transition: 'background .3s ease' }}
          >
            <span style={{ position: 'absolute', top: 2, left: strict ? 22 : 2, width: 18, height: 18, borderRadius: '50%', background: '#fff', transition: 'left .3s cubic-bezier(.34,1.56,.64,1)' }} />
          </span>
        </div>
      </div>
    </>
  );
}
