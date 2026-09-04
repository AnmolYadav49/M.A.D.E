import React from 'react';

const SAMPLE_ROWS = [
  { ts: '10:45:09.11', agent: 'Reviewer', action: 'Constraint verification passed', lat: '312ms', latColor: 'var(--dim2)', hash: 'b7e222…' },
  { ts: '10:44:51.88', agent: 'Sandbox', action: 'Execute script (attempt 2)', lat: '1.9s', latColor: 'var(--dim2)', hash: '9d34ac…' },
  { ts: '10:44:02.40', agent: 'Coder', action: 'Patch after sandbox failure', lat: '880ms', latColor: 'var(--dim2)', hash: '5f01bd…' },
  { ts: '10:43:36.19', agent: 'Sandbox', action: 'Execute script (attempt 1) — error', lat: '2.4s', latColor: 'var(--err)', hash: 'a7f92b…' },
  { ts: '10:42:58.03', agent: 'Researcher', action: 'Query enterprise constraints', lat: '450ms', latColor: 'var(--dim2)', hash: 'e38c11…' },
];

function hashOf(text, i) {
  let h = 0;
  const s = `${text}#${i}`;
  for (let k = 0; k < s.length; k++) h = (h * 31 + s.charCodeAt(k)) >>> 0;
  return h.toString(16).padStart(6, '0').slice(0, 6) + '…';
}

function liveRows(logs) {
  return [...logs].reverse().map((m, i) => ({
    ts: m.time, agent: m.role, action: m.text.split('\n')[0].slice(0, 80), lat: '—', latColor: 'var(--dim2)', hash: hashOf(m.text, i),
  }));
}

export default function AuditView({ visible, state }) {
  const rows = [...liveRows(state.logs), ...SAMPLE_ROWS];

  return (
    <section style={{ display: visible ? 'flex' : 'none', flexDirection: 'column', gap: 28, animation: 'fadeUp .4s ease both' }}>
      <header data-reveal="1" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: 18, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 8 }}>Trace Telemetry</div>
          <h1 style={{ fontFamily: "'Bodoni Moda',serif", fontWeight: 600, fontSize: 40, lineHeight: 1.1 }}>Audit Log</h1>
        </div>
        <button onClick={() => downloadJson(rows)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px', background: 'var(--fg)', color: 'var(--bg)', border: 'none', cursor: 'pointer', fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase' }}>
          <span className="mi" style={{ fontSize: 16 }}>download</span>Export JSON
        </button>
      </header>
      <div style={{ border: '1px solid var(--border)', overflowX: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 2.4fr 1fr 1fr', gap: 16, padding: '12px 20px', background: 'var(--panel)', fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
          <div>Timestamp</div><div>Agent</div><div>Action</div><div>Latency</div><div>Hash</div>
        </div>
        {rows.map((a, i) => (
          <div key={i} data-reveal="1" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 2.4fr 1fr 1fr', gap: 16, padding: '14px 20px', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--dim3)' }}>{a.ts}</div>
            <div style={{ fontSize: 13 }}>{a.agent}</div>
            <div style={{ fontSize: 13, color: 'var(--dim2)' }}>{a.action}</div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: a.latColor }}>{a.lat}</div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: 'var(--dim5)' }}>{a.hash}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function downloadJson(rows) {
  const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'made-audit-log.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
