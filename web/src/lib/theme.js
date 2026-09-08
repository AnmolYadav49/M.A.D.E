import { useLayoutEffect } from 'react';

// Ported from the Claude Design mockup's Component.applyTheme(). --ok/--warn/--err
// stay constant across themes; everything else swaps between the dark default and
// the "cream paper, dark ink" light variant, and --primary/--accent are always the
// user's chosen accent color.
const PALETTES = {
  light: {
    bg: '#fef8f5', card: '#ffffff', panel: '#f4efec', fg: '#1d1b1a', border: '#e4ded9', sand: '#EBD6C8',
    dim1: 'rgba(29,27,26,.92)', dim2: 'rgba(29,27,26,.66)', dim3: 'rgba(29,27,26,.55)', dim4: 'rgba(29,27,26,.48)', dim5: 'rgba(29,27,26,.32)',
    hair: 'rgba(29,27,26,.045)', glow: 'rgba(176,87,48,.14)', navbg: 'rgba(255,255,255,.7)', navborder: 'rgba(0,0,0,.07)',
  },
  dark: {
    bg: '#121212', card: '#1E1E1E', panel: '#171717', fg: '#ffffff', border: '#333333', sand: '#1E1E1E',
    dim1: 'rgba(255,255,255,.9)', dim2: 'rgba(255,255,255,.62)', dim3: 'rgba(255,255,255,.52)', dim4: 'rgba(255,255,255,.45)', dim5: 'rgba(255,255,255,.3)',
    hair: 'rgba(255,255,255,.04)', glow: 'rgba(255,255,255,.1)', navbg: 'rgba(30,30,30,.55)', navborder: 'rgba(255,255,255,.08)',
  },
};

export const STATIC_TOKENS = { ok: '#3f9d6d', warn: '#e0b341', err: '#e04a3c' };

export const ACCENT_SWATCHES = ['#b05730', '#3f7cad', '#4a8f6d', '#8a5cd1'];

export function applyTheme(rootEl, theme, accent) {
  if (!rootEl) return;
  const P = PALETTES[theme] || PALETTES.dark;
  const s = rootEl.style;
  Object.entries(P).forEach(([k, v]) => s.setProperty('--' + k, v));
  Object.entries(STATIC_TOKENS).forEach(([k, v]) => s.setProperty('--' + k, v));
  s.setProperty('--primary', accent);
  s.setProperty('--accent', accent);
  s.setProperty('background', P.bg);
  s.setProperty('color', P.fg);
}

export function useThemeVars(rootRef, theme, accent) {
  useLayoutEffect(() => {
    applyTheme(rootRef.current, theme, accent);
  }, [rootRef, theme, accent]);
}
