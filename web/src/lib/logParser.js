// The backend has no structured "phase" API (see /home/claude/anmolyadav49/m.a.d.e
// main.py: /execute-task blocks on the whole graph run and only returns the final
// state). What it does expose live is /ws/logs, which mirrors each node's
// `logging.info(...)` line (graph.py) as it happens. We pattern-match those known
// strings to drive the live pipeline tracker without touching the backend's log
// wording contract beyond what's already fixed at each call site there.
//
// `ctx` is small mutable state threaded across calls for one run, letting us tell a
// first Coder pass ("synthesizing") apart from a post-failure one ("patching") even
// though graph.py logs the identical message both times.

export function newRunContext() {
  return { sawFailure: false };
}

const MARKERS = [
  { match: 'RESEARCHER AGENT', phase: () => 'researching', role: 'Researcher', text: 'Analyzing the task and gathering technical context…' },
  { match: 'CODER AGENT', phase: (ctx) => (ctx.sawFailure ? 'patching' : 'synthesizing'), role: 'Coder', text: (ctx) => (ctx.sawFailure ? 'Patching the script after the sandbox failure…' : 'Synthesizing candidate Python code…') },
  { match: 'SANDBOX EXECUTOR', phase: () => 'sandbox', role: 'Sandbox', text: 'Running the candidate script in an isolated subprocess…' },
  { match: 'SANDBOX FAILED', phase: () => 'sandbox_failed', role: 'Sandbox', text: 'Execution failed — routing the traceback back to Coder for a repair pass.', onMatch: (ctx) => { ctx.sawFailure = true; } },
  { match: 'SANDBOX SUCCESS', phase: () => 'sandbox_ok', role: 'Sandbox', text: 'Execution clean — routing to Reviewer.' },
  { match: 'REVIEWER AGENT', phase: () => 'reviewing', role: 'Reviewer', text: 'Auditing the script for syntax, dependency and security issues…' },
];

export function parseLogLine(rawLine, ctx) {
  for (const m of MARKERS) {
    if (rawLine.includes(m.match)) {
      if (m.onMatch) m.onMatch(ctx);
      return {
        phase: m.phase(ctx),
        role: m.role,
        text: typeof m.text === 'function' ? m.text(ctx) : m.text,
      };
    }
  }
  return null;
}

// Per-node visual state, ported 1:1 from the Claude Design mockup's renderVals()
// node-state derivation so the tracker looks identical.
const NODE_DEFS = [
  { name: 'Researcher', symbol: 'search' },
  { name: 'Coder', symbol: 'code' },
  { name: 'Sandbox', symbol: 'terminal' },
  { name: 'Reviewer', symbol: 'fact_check' },
  { name: 'Gate', symbol: 'gavel' },
];

export const PHASE_META = {
  idle: { node: -1, status: 'IDLE', color: 'var(--dim3)', anim: 'none' },
  researching: { node: 0, status: 'RESEARCHING', color: 'var(--accent)', anim: 'blink 1.4s infinite' },
  synthesizing: { node: 1, status: 'SYNTHESIZING', color: 'var(--accent)', anim: 'blink 1.4s infinite' },
  sandbox: { node: 2, status: 'SANDBOX RUN', color: 'var(--accent)', anim: 'blink 1.4s infinite' },
  sandbox_failed: { node: 2, status: 'SELF-HEALING', color: 'var(--err)', anim: 'blink 1.4s infinite', error: true, healing: true },
  patching: { node: 1, status: 'PATCHING', color: 'var(--primary)', anim: 'blink 1.4s infinite', healing: true },
  sandbox_ok: { node: 2, status: 'SANDBOX RUN', color: 'var(--accent)', anim: 'blink 1.4s infinite' },
  reviewing: { node: 3, status: 'REVIEWING', color: 'var(--accent)', anim: 'blink 1.4s infinite' },
  awaiting_hitl: { node: 4, status: 'AWAITING HITL', color: 'var(--ok)', anim: 'blink 1.4s infinite', gate: true },
  running_subprocess: { node: 4, status: 'RUNNING SUBPROCESS', color: 'var(--warn)', anim: 'blink 1.4s infinite' },
  complete: { node: 5, status: 'COMPLETE', color: 'var(--ok)', anim: 'none', complete: true },
  error: { node: -1, status: 'ERROR', color: 'var(--err)', anim: 'none' },
  rejected: { node: -1, status: 'REJECTED', color: 'var(--err)', anim: 'none' },
  blocked: { node: 3, status: 'POLICY BLOCK', color: 'var(--err)', anim: 'none', error: true },
  exhausted: { node: 2, status: 'HEAL EXHAUSTED', color: 'var(--err)', anim: 'none', error: true },
};

export function computeNodes(phase) {
  const meta = PHASE_META[phase] || PHASE_META.idle;
  const active = meta.node;
  const nodes = NODE_DEFS.map((d, i) => {
    let st;
    if (meta.complete || i < active) st = 'done';
    else if (i === active && meta.error) st = 'error';
    else if (i === active && meta.healing) st = 'heal';
    else if (i === active) st = 'active';
    else st = 'idle';
    const M = {
      done: { bg: 'var(--card)', border: 'var(--fg)', icon: 'var(--fg)', label: 'var(--fg)', weight: '400', opacity: '1', scale: 'scale(1)', anim: 'none' },
      active: { bg: 'var(--fg)', border: 'var(--fg)', icon: 'var(--bg)', label: 'var(--fg)', weight: '700', opacity: '1', scale: 'scale(1.08)', anim: 'nodePulse 1.6s ease-in-out infinite' },
      heal: { bg: 'var(--primary)', border: 'var(--primary)', icon: '#fff', label: 'var(--fg)', weight: '700', opacity: '1', scale: 'scale(1.08)', anim: 'healPulse 1.4s ease-in-out infinite' },
      error: { bg: 'rgba(224,74,60,.14)', border: 'var(--err)', icon: 'var(--err)', label: 'var(--err)', weight: '700', opacity: '1', scale: 'scale(1.08)', anim: 'errPulse 1.2s ease-in-out infinite' },
      idle: { bg: 'var(--card)', border: 'var(--border)', icon: 'var(--dim3)', label: 'var(--dim4)', weight: '400', opacity: '.5', scale: 'scale(1)', anim: 'none' },
    }[st];
    return { name: d.name, symbol: d.symbol, ...M };
  });

  const posPct = ['0%', '25%', '50%', '75%', '100%'];
  const progressPct = meta.complete ? '100%' : (active < 0 ? '0%' : posPct[Math.min(active, 4)]);
  const healOn = !!meta.healing;

  return {
    meta, nodes, progressPct, healOn,
    healColor: healOn ? 'var(--accent)' : 'var(--dim5)',
    healDash: healOn ? 'dash 1s linear infinite' : 'none',
    healChipOpacity: healOn ? '1' : '.35',
  };
}
