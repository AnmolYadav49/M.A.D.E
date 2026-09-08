// Thin wrappers over the FastAPI backend. Relative URLs so this works both
// through the Vite dev proxy (see vite.config.js) and same-origin in production
// (main.py serves the built frontend/ and the API from the same FastAPI app).

const KEY_STORAGE = 'made_openrouter_key';
const SESSION_STORAGE = 'made_session_id';

// --- session id --------------------------------------------------------------
// Identifies this browser tab so the backend can route only this tab's log
// lines to it. Without it every visitor on a public deployment receives every
// other visitor's task text, generated code and output.
function makeId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function sessionId() {
  try {
    let id = window.sessionStorage.getItem(SESSION_STORAGE);
    if (!id) {
      id = makeId();
      window.sessionStorage.setItem(SESSION_STORAGE, id);
    }
    return id;
  } catch {
    // Storage blocked (private mode / embedded). Fall back to a per-load id;
    // logs still scope correctly for the lifetime of the page.
    if (!window.__madeSessionId) window.__madeSessionId = makeId();
    return window.__madeSessionId;
  }
}

// --- BYOK key handling -------------------------------------------------------
// sessionStorage, deliberately not localStorage: the key is cleared when the
// tab closes rather than persisting on a shared or public machine. It is sent
// per request and never stored server-side.
export function getApiKey() {
  try {
    return window.sessionStorage.getItem(KEY_STORAGE) || '';
  } catch {
    return window.__madeApiKey || '';
  }
}

export function setApiKey(key) {
  const clean = (key || '').trim();
  try {
    if (clean) window.sessionStorage.setItem(KEY_STORAGE, clean);
    else window.sessionStorage.removeItem(KEY_STORAGE);
  } catch {
    window.__madeApiKey = clean;
  }
}

export function clearApiKey() {
  setApiKey('');
}

/** Very light shape check so obvious paste errors are caught before a round trip. */
export function looksLikeOpenRouterKey(key) {
  return /^sk-or-v1-[A-Za-z0-9]{16,}$/.test((key || '').trim());
}

function serverApiKey() {
  try {
    return window.localStorage.getItem('made_api_key') || '';
  } catch {
    return '';
  }
}

async function postJson(path, body) {
  const headers = { 'Content-Type': 'application/json', 'X-Session-Id': sessionId() };
  const byok = getApiKey();
  if (byok) headers['X-OpenRouter-Key'] = byok;
  const srv = serverApiKey() || import.meta.env.VITE_MADE_API_KEY || '';
  if (srv) headers['X-API-Key'] = srv;

  const res = await fetch(path, { method: 'POST', headers, body: JSON.stringify(body) });
  if (!res.ok) {
    let detail;
    try { detail = (await res.json())?.detail; } catch { /* body not JSON */ }
    const err = new Error(detail || `${path} returned ${res.status}: ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export function executeTask(task) {
  return postJson('/execute-task', { task });
}

export function approveAndRun(proposedCode) {
  return postJson('/approve-and-run', { proposed_code: proposedCode, human_approved: true });
}

export function rejectTask() {
  return postJson('/reject-task', { session_id: 'default' });
}

export function logSocketUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/logs?session=${encodeURIComponent(sessionId())}`;
}

/** Deployment posture: public mode, whether execution is on, rate limits. */
export function healthCheck() {
  return fetch('/api/health').then((r) => r.json()).catch(() => null);
}
