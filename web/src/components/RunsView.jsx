import React from 'react';

const CHIP = {
  ok: { status: 'Complete', statusIcon: 'check', statusColor: 'var(--ok)', statusBg: 'rgba(63,157,109,.12)' },
  healed: { status: 'Healed', statusIcon: 'autorenew', statusColor: 'var(--accent)', statusBg: 'rgba(176,87,48,.12)' },
  fail: { status: 'Failed', statusIcon: 'close', statusColor: 'var(--err)', statusBg: 'rgba(224,74,60,.12)' },
  live: { status: 'Running', statusIcon: 'bolt', statusColor: 'var(--warn)', statusBg: 'rgba(224,179,65,.12)' },
  rejected: { status: 'Rejected', statusIcon: 'close', statusColor: 'var(--err)', statusBg: 'rgba(224,74,60,.12)' },
};

// The backend keeps no run-history store (see main.py — /execute-task is stateless
// per call), so most of this is illustrative sample history; the top row reflects
// the pipeline actually dispatched in this session, when there is one.
const SAMPLE_RUNS = [
  { id: 'RUN-4468', task: 'Reconcile Stripe payouts against ledger', dur: '6m 03s', loops: '0', loopColor: 'var(--dim4)', ...CHIP.ok },
  { id: 'RUN-4462', task: 'Migrate users table to new auth schema', dur: '18m 47s', loops: '2', loopColor: 'var(--accent)', ...CHIP.healed },
  { id: 'RUN-4455', task: 'Scrape + dedupe top 500 HN posts → Postgres', dur: '3m 21s', loops: '0', loopColor: 'var(--dim4)', ...CHIP.ok },
  { id: 'RUN-4449', task: 'Nightly rollup of event telemetry', dur: '—', loops: '3', loopColor: 'var(--err)', ...CHIP.fail },
];

function currentRunRow(state) {
  if (!state.task) return null;
  const chipKey = state.phase === 'complete' ? 'ok' : state.phase === 'rejected' ? 'rejected' : state.phase === 'error' ? 'fail' : 'live';
  const chip = CHIP[chipKey];
  return {
    id: 'RUN-LIVE', task: state.task, dur: state.running || chipKey === 'live' ? '…' : '—',
    loops: state.selfHealed ? '1' : '0', loopColor: state.selfHealed ? 'var(--accent)' : 'var(--dim4)', ...chip,
  };
}

export default function RunsView({ visible, state }) {
  const live = currentRunRow(state);
  const runs = live ? [live, ...SAMPLE_RUNS] : SAMPLE_RUNS;

  return (
    <section style={{ display: visible ? 'flex' : 'none', flexDirection: 'column', gap: 28, animation: 'fadeUp .4s ease both' }}>
      <header data-reveal="1" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 18 }}>
        <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 8 }}>Execution History</div>
        <h1 style={{ fontFamily: "'Bodoni Moda',serif", fontWeight: 600, fontSize: 40, lineHeight: 1.1 }}>Recent Runs</h1>
      </header>
      <div style={{ border: '1px solid var(--border)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 3fr 1fr 1fr 1fr', gap: 16, padding: '12px 20px', background: 'var(--panel)', fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
          <div>Run ID</div><div>Task</div><div>Duration</div><div>Loops</div><div style={{ textAlign: 'right' }}>Status</div>
        </div>
        {runs.map((r) => (
          <div key={r.id} data-reveal="1" style={{ display: 'grid', gridTemplateColumns: '1.4fr 3fr 1fr 1fr 1fr', gap: 16, padding: '16px 20px', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--accent)' }}>{r.id}</div>
            <div style={{ fontSize: 13, color: 'var(--dim1)' }}>{r.task}</div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'var(--dim2)' }}>{r.dur}</div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: r.loopColor }}>{r.loops}</div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, border: `1px solid ${r.statusColor}`, background: r.statusBg, color: r.statusColor, fontFamily: "'JetBrains Mono',monospace", fontSize: 10, textTransform: 'uppercase', padding: '3px 9px' }}>
                <span className="mi" style={{ fontSize: 12 }}>{r.statusIcon}</span>{r.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
