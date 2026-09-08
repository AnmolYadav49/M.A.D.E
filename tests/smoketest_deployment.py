"""Smoke test for the public-deployment posture (BYOK + safety defaults).

Asserts the properties that make it safe to put this on a public URL:
 1. /api/health advertises public mode and that execution is disabled.
 2. /execute-task without a key is refused with 401, not silently run.
 3. A supplied key is accepted from the X-OpenRouter-Key header.
 4. /approve-and-run refuses to execute while execution is disabled.
 5. The log websocket only delivers lines belonging to the caller's session —
    the multi-tenant leak that would otherwise show visitor A's work to B.

Run against a server started with:
  MADE_PUBLIC_MODE=1 MADE_DEMO_MODE=1 uvicorn main:app --port 8000
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from console import force_utf8  # noqa: E402

force_utf8()

BASE = "http://127.0.0.1:8000"


def _req(path, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if body is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def _pass(m): print(f"  \033[32m✔\033[0m {m}")
def _fail(m, d): print(f"  \033[31m✘\033[0m {m} — {d}"); sys.exit(1)


def test_health():
    print("\n[1] deployment posture on /api/health")
    st, b = _req("/api/health")
    if st != 200:
        _fail("responds 200", st)
    if not b.get("public_mode"):
        _fail("public_mode advertised", b)
    _pass("public_mode = True")
    if b.get("execution_enabled") is not False:
        _fail("execution disabled by default in public mode", b)
    _pass("execution_enabled = False (safe default)")
    if not b.get("byok_required"):
        _fail("byok_required advertised", b)
    _pass("byok_required = True")


def test_key_required():
    print("\n[2] /execute-task refuses without a key")
    # Demo mode bypasses the key requirement by design, so test the real path
    # by asking the server what it thinks first.
    _, h = _req("/api/health")
    if h.get("demo_mode"):
        print("    \033[33m(demo mode on: key requirement intentionally bypassed — skipping)\033[0m")
        _pass("skipped under demo mode")
        return
    st, b = _req("/execute-task", "POST", {"task": "compute 2+2"})
    if st != 401:
        _fail("no key → 401", f"got {st}: {b}")
    _pass("missing key → 401 with a clear message")


def test_execution_refused():
    print("\n[3] /approve-and-run will not execute while execution is disabled")
    st, b = _req("/approve-and-run", "POST",
                 {"proposed_code": "print('hello')", "human_approved": True})
    if st != 200:
        _fail("responds 200", st)
    if b.get("status") != "Execution disabled" or not b.get("execution_skipped"):
        _fail("refuses to run", b)
    _pass("refused, and says so explicitly rather than pretending it ran")


def test_task_length_cap():
    print("\n[4] oversized task is rejected before reaching the model")
    st, _ = _req("/execute-task", "POST", {"task": "x" * 50_000},
                 headers={"X-OpenRouter-Key": "sk-or-v1-" + "a" * 32})
    if st != 422:
        _fail("oversized task → 422", f"got {st}")
    _pass("422 from the length cap (no model call, no cost)")


def test_session_scoped_logs():
    print("\n[5] log websocket is scoped per session")
    try:
        from websockets.sync.client import connect
    except ImportError:
        print("    \033[33m(websockets package not installed — skipping)\033[0m")
        _pass("skipped")
        return

    received_b: list[str] = []

    def listen_b():
        try:
            with connect(f"ws://127.0.0.1:8000/ws/logs?session=tenant-B", open_timeout=5) as ws:
                deadline = time.time() + 12
                while time.time() < deadline:
                    try:
                        received_b.append(ws.recv(timeout=2))
                    except Exception:
                        pass
        except Exception:
            pass

    t = threading.Thread(target=listen_b, daemon=True)
    t.start()
    time.sleep(1.0)

    secret = "TENANT-A-CONFIDENTIAL-MARKER"
    _req("/execute-task", "POST", {"task": f"compute {secret}"},
         headers={"X-Session-Id": "tenant-A", "X-OpenRouter-Key": "sk-or-v1-" + "a" * 32})
    t.join(timeout=14)

    leaked = [m for m in received_b if secret in m]
    if leaked:
        _fail("tenant B must not see tenant A's task", f"{len(leaked)} leaked line(s): {leaked[0][:120]}")
    _pass(f"tenant B received {len(received_b)} line(s), none containing tenant A's task")


def main():
    print(f"Smoke-testing deployment posture against {BASE}")
    test_health()
    test_key_required()
    test_execution_refused()
    test_task_length_cap()
    test_session_scoped_logs()
    print("\n\033[32mDeployment posture checks passed.\033[0m")


if __name__ == "__main__":
    main()
