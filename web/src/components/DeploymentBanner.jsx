import React from 'react';

/**
 * States this deployment can be in that the operator needs to see immediately.
 *
 * The execution-disabled case matters most: without it a visitor watching the
 * pipeline reach the approval gate would reasonably assume the code had been
 * run and verified. It hasn't — on a public deployment the sandbox is off,
 * because static analysis is not a sandbox and running a stranger's generated
 * Python on the host is not something to do by default.
 */
export default function DeploymentBanner({ health, hasKey, onOpenKey }) {
  if (!health) return null;

  const banners = [];

  if (health.byok_required && !hasKey && !health.demo_mode) {
    banners.push({
      key: 'needs-key',
      tone: 'accent',
      icon: 'key',
      title: 'Add your OpenRouter key to run the pipeline',
      body: 'This is a public deployment, so runs use your own model key. It stays in this tab and is never stored server-side.',
      action: { label: 'Add key', onClick: onOpenKey },
    });
  }

  if (health.execution_enabled === false) {
    banners.push({
      key: 'no-exec',
      tone: 'warn',
      icon: 'gpp_maybe',
      title: 'Code execution is disabled on this deployment',
      body: 'The full graph still runs — research, synthesis, the policy audit, review and the human gate. Only the sandbox step is skipped, because executing visitor-supplied Python on a shared host is not safe without container isolation.',
    });
  }

  if (health.demo_mode) {
    banners.push({
      key: 'demo',
      tone: 'warn',
      icon: 'movie',
      title: 'Demo mode — agent responses are scripted',
      body: 'Graph routing, the policy audit and the self-heal loop all run for real; only the model text is canned. No API key needed.',
    });
  }

  if (!banners.length) return null;

  const TONES = {
    accent: { border: 'var(--primary)', bg: 'rgba(176,87,48,.08)', fg: 'var(--accent)' },
    warn: { border: 'var(--warn)', bg: 'rgba(224,179,65,.08)', fg: 'var(--warn)' },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
      {banners.map((b) => {
        const t = TONES[b.tone];
        return (
          <div
            key={b.key}
            style={{
              display: 'flex', alignItems: 'flex-start', gap: 14,
              border: `1px solid ${t.border}`, background: t.bg,
              padding: '14px 18px', animation: 'fadeUp .4s ease both',
            }}
          >
            <span className="mi" style={{ fontSize: 20, color: t.fg, flexShrink: 0, marginTop: 1 }}>{b.icon}</span>
            <div style={{ flexGrow: 1 }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: t.fg, marginBottom: 5 }}>
                {b.title}
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--dim2)', lineHeight: 1.6 }}>{b.body}</div>
            </div>
            {b.action && (
              <button
                onClick={b.action.onClick}
                style={{
                  flexShrink: 0, background: t.fg, color: 'var(--bg)', border: 'none',
                  cursor: 'pointer', padding: '9px 16px', borderRadius: 999,
                  fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
                  textTransform: 'uppercase', letterSpacing: '.05em',
                }}
              >
                {b.action.label}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
