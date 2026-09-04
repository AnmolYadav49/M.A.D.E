import React from 'react';

const GRAPH_NODES = [
  { name: 'Researcher', symbol: 'search', desc: 'Gathers methodology', long: 'Formulates the Python libraries and technical methodology needed for the task, grounded by the FAISS-backed local knowledge base.' },
  { name: 'Coder', symbol: 'code', desc: 'Writes the script', long: 'Translates the research methodology into clean, executable Python. Re-invoked with the sandbox’s traceback whenever a run fails — the self-heal loop.' },
  { name: 'Sandbox', symbol: 'terminal', desc: 'Runs in isolation', long: 'Executes the candidate script as an isolated subprocess with a hard timeout. On failure it routes stderr back to the Coder instead of surfacing a crash.' },
  { name: 'Reviewer', symbol: 'fact_check', desc: 'Verifies output', long: 'Performs a security and syntax audit — dangerous calls, missing imports — and produces the clearance report shown at the HITL gate.' },
  { name: 'Gate', symbol: 'gavel', desc: 'Human approval', long: 'Human-in-the-loop checkpoint. Approve executes the reviewed script against the real workspace; reject clears the generated workspace and terminates the run.' },
];

export default function GraphView({ visible }) {
  return (
    <section style={{ display: visible ? 'flex' : 'none', flexDirection: 'column', gap: 32, animation: 'fadeUp .4s ease both' }}>
      <header data-reveal="1" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 18 }}>
        <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 8 }}>LangGraph Topology</div>
        <h1 style={{ fontFamily: "'Bodoni Moda',serif", fontWeight: 600, fontSize: 40, lineHeight: 1.1 }}>Multi-Agent Pipeline</h1>
      </header>

      <div style={{ position: 'relative', border: '1px solid var(--border)', background: 'var(--panel)', padding: '60px 48px 96px' }}>
        <div style={{ position: 'absolute', top: 88, left: 100, right: 100, height: 1, background: 'var(--border)' }} />
        <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between' }}>
          {GRAPH_NODES.map((g) => (
            <div key={g.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, zIndex: 2 }}>
              <div style={{ width: 60, height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--card)', border: '1px solid var(--border)' }}>
                <span className="mi" style={{ fontSize: 28, color: 'var(--fg)' }}>{g.symbol}</span>
              </div>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase' }}>{g.name}</span>
              <span style={{ fontSize: 11, color: 'var(--dim4)', maxWidth: 120, textAlign: 'center', lineHeight: 1.4 }}>{g.desc}</span>
            </div>
          ))}
        </div>
        <svg viewBox="0 0 100 26" preserveAspectRatio="none" style={{ position: 'absolute', left: 100, right: 100, top: 118, width: 'calc(100% - 200px)', height: 70, overflow: 'visible' }}>
          <defs>
            <marker id="ah2" markerWidth="7" markerHeight="7" refX="4" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="var(--accent)" /></marker>
          </defs>
          <path d="M50 1 C 50 20, 26 20, 26 2" fill="none" stroke="var(--accent)" strokeWidth="0.7" strokeDasharray="2.4 2" markerEnd="url(#ah2)" style={{ animation: 'dash 1.2s linear infinite' }} vectorEffect="non-scaling-stroke" />
        </svg>
        <div style={{ position: 'absolute', bottom: 40, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 28 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--accent)' }}>
            <span style={{ width: 16, height: 2, background: 'var(--accent)', display: 'inline-block' }} />on sandbox failure → self-heal
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 1, background: 'var(--border)', border: '1px solid var(--border)' }}>
        {GRAPH_NODES.map((g) => (
          <div key={g.name} data-reveal="1" style={{ background: 'var(--card)', padding: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <span className="mi" style={{ fontSize: 20, color: 'var(--accent)' }}>{g.symbol}</span>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase' }}>{g.name}</span>
            </div>
            <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--dim2)' }}>{g.long}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
