import React from 'react';

export default function ApprovalBar({ visible, onReject, onApprove }) {
  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 72, right: 0, background: 'var(--card)', borderTop: '1px solid var(--border)',
      padding: '16px 48px', zIndex: 50, boxShadow: '0 -10px 40px rgba(0,0,0,.35)',
      display: visible ? 'flex' : 'none', justifyContent: 'space-between', alignItems: 'center', gap: 24,
      animation: 'fadeUp .3s ease both',
    }}>
      <div>
        <div style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 20 }}>Human-in-the-loop review</div>
        <div style={{ fontSize: 13, color: 'var(--dim2)', marginTop: 2 }}>Reviewer cleared the patched script. Authorize execution against the workspace.</div>
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        <button onClick={onReject} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 22px', background: 'transparent', border: '1px solid var(--primary)', color: 'var(--accent)', borderRadius: 999, cursor: 'pointer', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, letterSpacing: '.05em', textTransform: 'uppercase' }}>
          <span className="mi" style={{ fontSize: 16 }}>close</span>Reject
        </button>
        <button data-magnetic="1" onClick={onApprove} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '12px 26px', background: 'var(--fg)', color: 'var(--bg)', border: 'none', borderRadius: 999, cursor: 'pointer', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, letterSpacing: '.05em', textTransform: 'uppercase' }}>
          <span className="mi" style={{ fontSize: 16 }}>play_arrow</span>Approve &amp; Run
        </button>
      </div>
    </div>
  );
}
