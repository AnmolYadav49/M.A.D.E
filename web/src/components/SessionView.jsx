import React, { useMemo, useState } from 'react';
import { computeNodes } from '../lib/logParser';
import { ROLE_STYLE } from '../lib/roles';
import { diffLines, plainLines } from '../lib/diff';

const IDLE_PHASES = new Set(['idle', 'rejected']);
const DEFAULT_TASK_HINT = 'e.g. Backfill missing embeddings for 2,000,000 support tickets into the vector store';

export default function SessionView({ visible, pipeline }) {
  const { state, dispatch, approve, reject, reset } = pipeline;
  const [draft, setDraft] = useState('');
  const { meta, nodes, progressPct, healColor, healDash, healChipOpacity } = useMemo(() => computeNodes(state.phase), [state.phase]);

  const isIdle = IDLE_PHASES.has(state.phase);
  const showWork = !isIdle;
  const rows = state.selfHealed && state.priorCode
    ? diffLines(state.priorCode, state.code)
    : plainLines(state.code || (state.running ? '// agents are working…' : '// no code generated yet'));

  const submit = () => {
    const text = draft.trim();
    if (!text || state.running) return;
    dispatch(text);
    setDraft('');
  };

  return (
    <section style={{ display: visible ? 'flex' : 'none', flexDirection: 'column', gap: 36, animation: 'fadeUp .4s ease both', position: 'relative' }}>
      <header data-reveal="1" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: 18, gap: 24, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 8 }}>Agent Control Session</div>
          <h1 data-hero="1" style={{ fontFamily: "'Bodoni Moda',serif", fontWeight: 600, fontSize: 44, lineHeight: 1.1, letterSpacing: '-.01em' }}>{state.task || 'Agent Control Session'}</h1>
          <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--dim3)', marginTop: 10 }}>M.A.D.E. LangGraph pipeline · researcher → coder → sandbox → reviewer → gate</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={reset} disabled={state.running} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px', background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim2)', cursor: state.running ? 'not-allowed' : 'pointer', opacity: state.running ? 0.5 : 1, fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.05em', textTransform: 'uppercase' }}>
            <span className="mi" style={{ fontSize: 16 }}>restart_alt</span>New session
          </button>
        </div>
      </header>

      <div style={{ position: 'relative', padding: '8px 40px 0' }}>
        <div style={{ position: 'absolute', top: 36, left: 70, right: 70, height: 1, background: 'var(--border)' }} />
        <div style={{ position: 'absolute', top: 36, left: 70, height: 2, background: 'var(--fg)', width: progressPct, maxWidth: 'calc(100% - 140px)', transition: 'width .5s ease' }} />
        <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between' }}>
          {nodes.map((node) => (
            <div key={node.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, opacity: node.opacity, transition: 'opacity .4s ease', zIndex: 2 }}>
              <div style={{ width: 56, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', background: node.bg, border: `1px solid ${node.border}`, transition: 'all .4s ease', transform: node.scale, animation: node.anim }}>
                <span className="mi" style={{ fontSize: 26, color: node.icon }}>{node.symbol}</span>
              </div>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: node.label, fontWeight: node.weight }}>{node.name}</span>
            </div>
          ))}
        </div>
        <svg viewBox="0 0 100 20" preserveAspectRatio="none" style={{ position: 'absolute', left: 40, right: 40, top: 64, width: 'calc(100% - 80px)', height: 44, overflow: 'visible' }}>
          <defs><marker id="ah" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill={healColor} /></marker></defs>
          <path d="M50 1 C 50 16, 30 16, 30 2" fill="none" stroke={healColor} strokeWidth="0.7" strokeDasharray="2.4 2" markerEnd="url(#ah)" style={{ animation: healDash }} vectorEffect="non-scaling-stroke" />
        </svg>
        <div style={{ position: 'absolute', top: 112, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: healColor, border: `1px solid ${healColor}`, padding: '4px 10px', borderRadius: 999, opacity: healChipOpacity, transition: 'opacity .4s' }}>
            <span className="mi" style={{ fontSize: 13 }}>autorenew</span>Self-heal loop · Sandbox → Coder
          </span>
        </div>
      </div>

      {state.phase === 'error' && state.errorMessage && (
        <div data-reveal="1" style={{ display: 'flex', alignItems: 'center', gap: 10, border: '1px solid var(--err)', background: 'rgba(224,74,60,.08)', color: 'var(--err)', padding: '12px 16px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
          <span className="mi" style={{ fontSize: 18 }}>error</span>{state.errorMessage}
        </div>
      )}

      <div style={{ display: isIdle ? 'flex' : 'none', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20, border: '1px dashed var(--border)', padding: '64px 24px', margin: '44px 0 0' }}>
        <span className="mi" style={{ fontSize: 44, color: 'var(--dim5)' }}>rocket_launch</span>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 22, marginBottom: 6 }}>Pipeline idle</div>
          <p style={{ fontSize: 13, color: 'var(--dim3)', maxWidth: 420, lineHeight: 1.6 }}>The Researcher → Coder → Sandbox → Reviewer → Gate graph is armed. Describe a data task to watch the agents work in real time.</p>
        </div>
        <div style={{ display: 'flex', gap: 8, width: '100%', maxWidth: 480 }}>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder={DEFAULT_TASK_HINT}
            style={{ flexGrow: 1, background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--fg)', fontFamily: "'Inter',sans-serif", fontSize: 13, padding: '10px 12px', outline: 'none' }}
          />
        </div>
        <button data-magnetic="1" onClick={submit} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 24px', background: 'var(--fg)', color: 'var(--bg)', border: 'none', cursor: 'pointer', fontFamily: "'JetBrains Mono',monospace", fontSize: 12, letterSpacing: '.06em', textTransform: 'uppercase', borderRadius: 999 }}>
          <span className="mi" style={{ fontSize: 18 }}>bolt</span>Dispatch pipeline
        </button>
        {state.errorMessage && (
          <p style={{ fontSize: 12, color: 'var(--err)', fontFamily: "'JetBrains Mono',monospace" }}>{state.errorMessage}</p>
        )}
      </div>

      <div style={{ display: showWork ? 'grid' : 'none', gap: 1, background: 'var(--border)', border: '1px solid var(--border)', marginTop: 8, gridTemplateColumns: '1fr 1fr' }}>
        <div data-reveal="1" style={{ background: 'var(--card)', display: 'flex', flexDirection: 'column', height: 560 }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--dim2)' }}>Session Log</span>
            <span className="mi" style={{ fontSize: 16, color: 'var(--dim3)' }}>history</span>
          </div>
          <div style={{ flexGrow: 1, overflowY: 'auto', padding: 22, display: 'flex', flexDirection: 'column', gap: 22 }}>
            {state.logs.map((m, i) => {
              const style = ROLE_STYLE[m.role] || ROLE_STYLE.Coder;
              return (
                <div key={i} style={{ display: 'flex', gap: 14, animation: 'fadeUp .4s ease both' }}>
                  <div style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: style.avBg, border: `1px solid ${style.avBorder}` }}>
                    <span className="mi" style={{ fontSize: 16, color: style.avColor }}>{style.avIcon}</span>
                  </div>
                  <div style={{ flexGrow: 1, paddingTop: 2 }}>
                    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.04em', color: style.roleColor, marginBottom: 5 }}>{m.role} · {m.time}</div>
                    <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--dim1)', whiteSpace: 'pre-wrap' }}>{m.text}</p>
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ padding: '14px 18px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
              placeholder={state.running ? 'Pipeline running…' : 'Describe a new task…'}
              disabled={state.running}
              style={{ flexGrow: 1, background: 'transparent', border: 'none', borderBottom: '1px solid var(--border)', color: '#e5e5e5', fontFamily: "'Inter',sans-serif", fontSize: 13, padding: '8px 2px', outline: 'none' }}
            />
            <button onClick={submit} disabled={state.running} style={{ width: 32, height: 32, background: 'var(--accent)', border: 'none', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: state.running ? 'not-allowed' : 'pointer', opacity: state.running ? 0.5 : 1 }}>
              <span className="mi" style={{ fontSize: 16, color: '#fff' }}>send</span>
            </button>
          </div>
        </div>

        <div data-reveal="1" style={{ background: 'var(--card)', display: 'flex', flexDirection: 'column', height: 560 }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.04em', textTransform: 'uppercase' }}>generated_script.py</span>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: 'var(--dim3)', border: '1px solid var(--border)', padding: '1px 6px', textTransform: 'uppercase' }}>Python</span>
              {state.selfHealed && (
                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: 'var(--accent)', border: '1px solid var(--accent)', padding: '1px 6px', textTransform: 'uppercase' }}>Patched · self-heal</span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <span className="mi" style={{ fontSize: 16, color: 'var(--dim3)', cursor: 'pointer' }} onClick={() => state.code && navigator.clipboard.writeText(state.code)} title="Copy code">content_copy</span>
              <span className="mi" style={{ fontSize: 16, color: 'var(--dim3)', cursor: 'pointer' }} onClick={() => downloadCode(state.code)} title="Download code">download</span>
            </div>
          </div>
          <div style={{ flexGrow: 1, overflow: 'auto', fontFamily: "'JetBrains Mono',monospace", fontSize: 13, lineHeight: 1.75 }}>
            {rows.map((ln) => {
              const color = ln.kind === 'del' ? 'rgba(224,74,60,.9)' : ln.kind === 'add' ? 'rgba(120,200,150,.95)' : 'var(--dim1)';
              const rowBg = ln.kind === 'del' ? 'rgba(224,74,60,.08)' : ln.kind === 'add' ? 'rgba(63,157,109,.10)' : 'transparent';
              const mColor = ln.kind === 'del' ? 'var(--err)' : ln.kind === 'add' ? 'var(--ok)' : 'transparent';
              return (
                <div key={ln.n} style={{ display: 'flex', background: rowBg }}>
                  <span style={{ width: 34, flexShrink: 0, textAlign: 'right', padding: '0 8px', color: 'var(--dim5)', userSelect: 'none', background: 'var(--hair)' }}>{ln.n}</span>
                  <span style={{ width: 16, flexShrink: 0, textAlign: 'center', color: mColor }}>{ln.marker}</span>
                  <span style={{ whiteSpace: 'pre', color, paddingRight: 16 }}>{ln.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div style={{ display: showWork ? 'flex' : 'none', flexDirection: 'column', gap: 14, marginTop: 8 }}>
        <h3 data-reveal="1" style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 22, borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>Security Audit</h3>
        <div style={{ border: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, padding: '12px 16px', background: 'var(--panel)', fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
            <div>Check</div><div style={{ textAlign: 'right' }}>Status</div>
          </div>
          <AuditRow label="Sandbox Execution" detail={state.selfHealed ? 'Failed first attempt (OOM/error) · self-healed and re-verified' : 'Clean on first attempt · isolated subprocess'} pass={state.phase !== 'error' && !isIdle} />
          <AuditRow label="Human Authorization" detail={state.phase === 'complete' ? 'Approved and executed' : state.phase === 'rejected' ? 'Rejected · workspace cleared' : 'Awaiting operator sign-off'} pass={state.phase === 'complete'} pending={state.phase === 'awaiting_hitl' || state.phase === 'running_subprocess'} />
        </div>
        {state.reviewerReport && (
          <div data-reveal="1" style={{ border: '1px solid var(--border)', background: 'var(--panel)', padding: 16 }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)', marginBottom: 8 }}>Reviewer Security Report</div>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--dim1)', whiteSpace: 'pre-wrap' }}>{state.reviewerReport}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function AuditRow({ label, detail, pass, pending }) {
  const color = pending ? 'var(--warn)' : pass ? 'var(--primary)' : 'var(--err)';
  const bg = pending ? 'rgba(224,179,65,.12)' : pass ? 'rgba(176,87,48,.12)' : 'rgba(224,74,60,.12)';
  const icon = pending ? 'hourglass_empty' : pass ? 'check' : 'close';
  const text = pending ? 'Pending' : pass ? 'Pass' : 'Fail';
  return (
    <div data-reveal="1" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, padding: '13px 16px', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
      <div>
        <div style={{ fontSize: 13 }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--dim2)', marginTop: 2 }}>{detail}</div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, border: `1px solid ${color}`, background: bg, color, fontFamily: "'JetBrains Mono',monospace", fontSize: 10, textTransform: 'uppercase', padding: '3px 8px' }}>
          <span className="mi" style={{ fontSize: 12 }}>{icon}</span>{text}
        </span>
      </div>
    </div>
  );
}

function downloadCode(code) {
  if (!code) return;
  const blob = new Blob([code], { type: 'text/x-python' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'generated_script.py';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
