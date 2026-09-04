import React, { useMemo, useState } from 'react';
import { computeNodes } from '../lib/logParser';
import { ROLE_STYLE } from '../lib/roles';
import { diffLines, plainLines } from '../lib/diff';

const IDLE_PHASES = new Set(['idle', 'rejected']);
const DEFAULT_TASK_HINT = 'Describe a data task, or pick a demo prompt below';

// Preset prompts a judge can click to see the pipeline actually run. Picked to
// (a) be tiny enough to complete inside the sandbox's 10s timeout, (b) not need
// network egress (which the sandbox blocks), and (c) show visibly different
// output styles in the session log / code diff.
const DEMO_PROMPTS = [
  { icon: 'calculate', label: 'Primes to 200 (Sieve of Eratosthenes)', task: 'Write Python that computes every prime number up to 200 using the Sieve of Eratosthenes and prints them, comma-separated, on one line.' },
  { icon: 'table_view', label: 'Summarize mock_data.csv', task: 'Read the file mock_data.csv from the current working directory, print the header row, then print the total row count and the first 5 data rows.' },
  { icon: 'casino', label: 'Roll two dice 1000 times', task: 'Simulate rolling two six-sided dice 1000 times, then print a plain-text histogram of the sum distribution (2 through 12), one row per sum, using # characters as bars.' },
];

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

  const runPreset = (task) => {
    if (state.running) return;
    setDraft(task);
    dispatch(task);
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
          <p style={{ fontSize: 13, color: 'var(--dim3)', maxWidth: 420, lineHeight: 1.6 }}>The Researcher → Coder → Sandbox → Reviewer → Gate graph is armed. Describe a data task, or pick a ready-made one below to watch the agents work.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
            Try a demo prompt
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 720 }}>
            {DEMO_PROMPTS.map((p, i) => (
              <button
                key={p.label}
                className="demo-chip"
                onClick={() => runPreset(p.task)}
                title={p.task}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '9px 16px', background: 'rgba(176,87,48,.08)',
                  border: '1px solid var(--primary)', color: 'var(--accent)',
                  borderRadius: 999, cursor: 'pointer',
                  fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
                  letterSpacing: '.04em', textTransform: 'uppercase',
                  animation: 'chipIn .6s cubic-bezier(.34,1.56,.64,1) both',
                  animationDelay: `${0.15 + i * 0.09}s`,
                  transition: 'background .2s ease, transform .2s ease, box-shadow .2s ease, color .2s ease',
                }}
              >
                <span className="mi" style={{ fontSize: 15 }}>{p.icon}</span>{p.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, width: '100%', maxWidth: 480, marginTop: 6 }}>
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
        {(state.phase === 'blocked' || state.phase === 'exhausted') && (
          <div data-reveal="1" style={{ display: 'flex', alignItems: 'center', gap: 12, border: '1px solid var(--err)', background: 'rgba(224,74,60,.08)', color: 'var(--err)', padding: '14px 18px', fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
            <span className="mi" style={{ fontSize: 20 }}>{state.phase === 'blocked' ? 'gpp_bad' : 'block'}</span>
            <div>
              <div style={{ textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 4 }}>
                {state.phase === 'blocked' ? 'AST audit refused this code' : `Self-heal exhausted after ${state.healAttempts} attempts`}
              </div>
              <div style={{ color: 'var(--dim2)', fontSize: 11 }}>
                Failure class: <span style={{ color: 'var(--err)' }}>{state.failureClass}</span> · No approval bar will appear. Reset the session to try a different task.
              </div>
            </div>
          </div>
        )}

        {state.researchSources && state.researchSources.length > 0 && (
          <div data-reveal="1" style={{ border: '1px solid var(--border)', background: 'var(--panel)', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="mi" style={{ fontSize: 14, color: 'var(--accent)' }}>library_books</span>
              Grounded in {state.researchSources.length} FAISS methodology docs
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {state.researchSources.map((r, i) => (
                <span key={i} title={r.snippet} style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: 'var(--accent)', border: '1px solid var(--primary)', padding: '3px 10px', borderRadius: 999, background: 'rgba(176,87,48,.08)' }}>
                  {r.title}
                </span>
              ))}
            </div>
          </div>
        )}

        <h3 data-reveal="1" style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 22, borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>Security Audit</h3>
        <div style={{ border: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 3fr 0.5fr 1fr', gap: 16, padding: '12px 16px', background: 'var(--panel)', fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
            <div>Check</div><div>Detail</div><div>Line</div><div style={{ textAlign: 'right' }}>Verdict</div>
          </div>

          {/* Real deterministic AST audit rows from graph.reviewer_node — these come straight from security.py, not LLM prose. */}
          {state.securityAudit && state.securityAudit.findings.map((f, i) => (
            <AuditRow key={`ast-${i}`} label={f.check} detail={f.detail} line={f.line} severity={f.severity} />
          ))}

          {/* Runtime rows (not part of the AST audit but part of the pipeline's guardrails). */}
          <AuditRow
            label="Sandbox Execution"
            detail={state.failureClass === 'exhausted'
              ? `Failed ${state.healAttempts} attempts (${state.failureClass}) — no clean run`
              : state.selfHealed
                ? `Failed first attempt (${state.failureClass || 'runtime'}) · self-healed and re-verified`
                : (state.phase === 'awaiting_hitl' || state.phase === 'complete' || state.phase === 'running_subprocess')
                  ? 'Clean on first attempt · isolated subprocess'
                  : 'Not yet run'}
            severity={state.phase === 'exhausted' || state.phase === 'error' ? 'block' : (state.phase === 'awaiting_hitl' || state.phase === 'complete' || state.phase === 'running_subprocess') ? 'pass' : 'warn'}
          />
          <AuditRow
            label="Human Authorization"
            detail={state.phase === 'complete' ? 'Approved and executed' : state.phase === 'rejected' ? 'Rejected · workspace cleared' : state.phase === 'awaiting_hitl' || state.phase === 'running_subprocess' ? 'Awaiting operator sign-off' : 'N/A — pipeline terminated before HITL gate'}
            severity={state.phase === 'complete' ? 'pass' : state.phase === 'awaiting_hitl' || state.phase === 'running_subprocess' ? 'warn' : 'block'}
          />
        </div>

        {state.reviewerReport && (
          <div data-reveal="1" style={{ border: '1px solid var(--border)', background: 'var(--panel)', padding: 16 }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)', marginBottom: 8 }}>Reviewer Notes (deterministic verdict + LLM commentary)</div>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--dim1)', whiteSpace: 'pre-wrap' }}>{state.reviewerReport}</p>
          </div>
        )}
      </div>
    </section>
  );
}

const SEVERITY = {
  pass: { color: 'var(--ok)', bg: 'rgba(63,157,109,.12)', icon: 'check', text: 'Pass' },
  warn: { color: 'var(--warn)', bg: 'rgba(224,179,65,.12)', icon: 'hourglass_empty', text: 'Pending' },
  block: { color: 'var(--err)', bg: 'rgba(224,74,60,.12)', icon: 'block', text: 'Block' },
};

function AuditRow({ label, detail, line, severity }) {
  const s = SEVERITY[severity] || SEVERITY.warn;
  return (
    <div data-reveal="1" style={{ display: 'grid', gridTemplateColumns: '1.6fr 3fr 0.5fr 1fr', gap: 16, padding: '13px 16px', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
      <div style={{ fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 12, color: 'var(--dim2)' }}>{detail}</div>
      <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: 'var(--dim3)' }}>{line ?? ''}</div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, border: `1px solid ${s.color}`, background: s.bg, color: s.color, fontFamily: "'JetBrains Mono',monospace", fontSize: 10, textTransform: 'uppercase', padding: '3px 8px' }}>
          <span className="mi" style={{ fontSize: 12 }}>{s.icon}</span>{s.text}
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
