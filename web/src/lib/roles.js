// Avatar styling per session-log speaker, ported from the mockup's agent/user/sys
// avatar constants.
export const ROLE_STYLE = {
  Operator: { avBg: 'var(--fg)', avBorder: 'var(--fg)', avColor: 'var(--bg)', avIcon: 'person', roleColor: 'var(--accent)' },
  Researcher: { avBg: 'var(--hair)', avBorder: 'var(--dim5)', avColor: 'var(--fg)', avIcon: 'search', roleColor: 'var(--dim3)' },
  Coder: { avBg: 'var(--hair)', avBorder: 'var(--dim5)', avColor: 'var(--fg)', avIcon: 'code', roleColor: 'var(--dim3)' },
  Sandbox: { avBg: 'rgba(176,87,48,.14)', avBorder: 'var(--primary)', avColor: 'var(--accent)', avIcon: 'dns', roleColor: 'var(--accent)' },
  Reviewer: { avBg: 'var(--hair)', avBorder: 'var(--dim5)', avColor: 'var(--fg)', avIcon: 'fact_check', roleColor: 'var(--dim3)' },
  Subprocess: { avBg: 'rgba(176,87,48,.14)', avBorder: 'var(--primary)', avColor: 'var(--accent)', avIcon: 'dns', roleColor: 'var(--accent)' },
};

export function timeNow() {
  return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: false });
}
