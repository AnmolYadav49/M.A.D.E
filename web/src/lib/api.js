// Thin wrappers over the FastAPI backend. Relative URLs so this works both
// through the Vite dev proxy (see vite.config.js) and same-origin in production
// (main.py serves the built frontend/ and the API from the same FastAPI app).

async function postJson(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`${path} returned ${res.status}: ${res.statusText}`);
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
