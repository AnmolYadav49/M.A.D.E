import React, { useEffect, useState } from 'react';
import { getApiKey, setApiKey, clearApiKey, looksLikeOpenRouterKey } from '../lib/api';

/** Masked preview, e.g. sk-or-v1-abcd…7f2a — never renders the whole key. */
function maskKey(key) {
  if (!key) return '';
  if (key.length <= 16) return `${key.slice(0, 6)}…`;
  return `${key.slice(0, 12)}…${key.slice(-4)}`;
}

export default function ApiKeyModal({ open, onClose, onSaved, required }) {
  const [value, setValue] = useState('');
  const [reveal, setReveal] = useState(false);
  const [touched, setTouched] = useState(false);
  const existing = getApiKey();

  useEffect(() => {
    if (open) { setValue(''); setReveal(false); setTouched(false); }
  }, [open]);

  const trimmed = value.trim();
  const invalid = touched && trimmed.length > 0 && !looksLikeOpenRouterKey(trimmed);

  const save = () => {
    setTouched(true);
    if (!trimmed || !looksLikeOpenRouterKey(trimmed)) return;
    setApiKey(trimmed);
    onSaved?.();
    onClose();
  };

  const forget = () => {
    clearApiKey();
    onSaved?.();
    setValue('');
  };

  return (
    <>
      <div
        onClick={required && !existing ? undefined : onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.6)',
          backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
          zIndex: 100, opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity .3s ease',
        }}
      />
      <div style={{
        position: 'fixed', top: '50%', left: '50%', width: '92%', maxWidth: 540,
        background: 'var(--card)', border: '1px solid var(--border)', zIndex: 105,
        padding: 28, display: 'flex', flexDirection: 'column', gap: 18,
        opacity: open ? 1 : 0, pointerEvents: open ? 'auto' : 'none',
        transform: `translate(-50%,-50%) ${open ? 'scale(1)' : 'scale(.96)'}`,
        transition: 'opacity .3s ease, transform .35s cubic-bezier(.16,1,.3,1)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
          <div>
            <h3 style={{ fontFamily: "'Bodoni Moda',serif", fontSize: 24, display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="mi" style={{ fontSize: 24, color: 'var(--accent)' }}>key</span>
              Use your own API key
            </h3>
            <p style={{ fontSize: 12.5, color: 'var(--dim2)', marginTop: 8, lineHeight: 1.6 }}>
              This deployment doesn't ship with a shared model key, so runs use yours.
            </p>
          </div>
          {(!required || existing) && (
            <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--dim3)', cursor: 'pointer', display: 'flex' }}>
              <span className="mi" style={{ fontSize: 20 }}>close</span>
            </button>
          )}
        </div>

        {existing && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, border: '1px solid var(--ok)', background: 'rgba(63,157,109,.10)', padding: '10px 14px' }}>
            <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11.5, color: 'var(--ok)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="mi" style={{ fontSize: 15 }}>check_circle</span>
              Key set · {maskKey(existing)}
            </span>
            <button onClick={forget} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim2)', cursor: 'pointer', fontFamily: "'JetBrains Mono',monospace", fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '.05em', padding: '5px 10px' }}>
              Forget key
            </button>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
            OpenRouter API key
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type={reveal ? 'text' : 'password'}
              value={value}
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => setValue(e.target.value)}
              onBlur={() => setTouched(true)}
              onKeyDown={(e) => { if (e.key === 'Enter') save(); }}
              placeholder="sk-or-v1-…"
              style={{
                flexGrow: 1, background: 'var(--panel)',
                border: `1px solid ${invalid ? 'var(--err)' : 'var(--border)'}`,
                color: 'var(--fg)', fontFamily: "'JetBrains Mono',monospace",
                fontSize: 13, padding: '11px 12px', outline: 'none',
              }}
            />
            <button
              onClick={() => setReveal((r) => !r)}
              title={reveal ? 'Hide' : 'Show'}
              style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim3)', cursor: 'pointer', width: 44, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <span className="mi" style={{ fontSize: 18 }}>{reveal ? 'visibility_off' : 'visibility'}</span>
            </button>
          </div>
          {invalid && (
            <span style={{ fontSize: 11.5, color: 'var(--err)', fontFamily: "'JetBrains Mono',monospace" }}>
              That doesn't look like an OpenRouter key — they start with sk-or-v1-
            </span>
          )}
          <a
            href="https://openrouter.ai/keys"
            target="_blank"
            rel="noreferrer noopener"
            style={{ fontSize: 12, color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 5 }}
          >
            Get a free key at openrouter.ai/keys
            <span className="mi" style={{ fontSize: 14 }}>open_in_new</span>
          </a>
        </div>

        {/* Being explicit about handling matters more than the feature itself:
            people are reasonably wary of pasting a key into someone's demo. */}
        <div style={{ border: '1px solid var(--border)', background: 'var(--panel)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--dim3)' }}>
            How your key is handled
          </div>
          {[
            ['lock', 'Kept in this tab\'s sessionStorage — cleared when you close the tab.'],
            ['cloud_off', 'Never written to the server\'s disk, database or logs.'],
            ['bolt', 'Sent on each request, used for that request, then dropped.'],
            ['visibility_off', 'Redacted from the log stream if it ever appears in one.'],
          ].map(([icon, text]) => (
            <div key={text} style={{ display: 'flex', gap: 9, alignItems: 'flex-start', fontSize: 12.5, color: 'var(--dim2)', lineHeight: 1.5 }}>
              <span className="mi" style={{ fontSize: 15, color: 'var(--accent)', flexShrink: 0, marginTop: 1 }}>{icon}</span>
              {text}
            </div>
          ))}
          <div style={{ fontSize: 11.5, color: 'var(--dim3)', lineHeight: 1.55, marginTop: 2 }}>
            You can verify all of this in <code style={{ fontFamily: "'JetBrains Mono',monospace" }}>main.py</code> and{' '}
            <code style={{ fontFamily: "'JetBrains Mono',monospace" }}>runcontext.py</code>. If you'd rather not paste a key
            anywhere, clone the repo and run it locally instead.
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          {(!required || existing) && (
            <button onClick={onClose} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--dim2)', cursor: 'pointer', padding: '11px 18px', fontFamily: "'JetBrains Mono',monospace", fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '.05em' }}>
              Cancel
            </button>
          )}
          <button
            onClick={save}
            disabled={!trimmed}
            style={{
              background: trimmed ? 'var(--fg)' : 'var(--border)',
              color: trimmed ? 'var(--bg)' : 'var(--dim3)',
              border: 'none', cursor: trimmed ? 'pointer' : 'not-allowed',
              padding: '11px 22px', fontFamily: "'JetBrains Mono',monospace",
              fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '.05em',
              display: 'flex', alignItems: 'center', gap: 7,
            }}
          >
            <span className="mi" style={{ fontSize: 16 }}>vpn_key</span>Save key
          </button>
        </div>
      </div>
    </>
  );
}
