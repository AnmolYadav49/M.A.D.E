// Thin wrappers over the FastAPI backend. Relative URLs so this works both
// through the Vite dev proxy (see vite.config.js) and same-origin in production
// (main.py serves the built frontend/ and the API from the same FastAPI app).
//
// If MADE_API_KEY is set on the server, the client must send it as an X-API-Key
// header. In dev, either drop VITE_MADE_API_KEY in web/.env or set it in
// localStorage("made_api_key") — no key is needed against a server that itself
// has no key set.

function apiKey() {
  try {
    const fromStorage = window.localStorage.getItem('made_api_key');
    if (fromStorage) return fromStorage;
  } catch { /* private-mode / storage disabled */ }
  return import.meta.env.VITE_MADE_API_KEY || '';
}

async function postJson(path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const key = apiKey();
  if (key) headers['X-API-Key'] = key;
  const res = await fetch(path, { method: 'POST', headers, body: JSON.stringify(body) });
  if (!res.ok) {
    let detail;
    try { detail = (await res.json())?.detail; } catch { /* body not JSON */ }
    throw new Error(detail ? `${path} → ${res.status}: ${detail}` : `${path} returned ${res.status}: ${res.statusText}`);
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
  return `${proto}://${window.location.host}/ws/logs`;
}

export function healthCheck() {
  return fetch('/api/health').then((r) => r.json()).catch(() => null);
}
