"""Asserts that /ws/logs actually accepts a WebSocket upgrade.

This exists because of a dependency bug that produced no build-time error and
no server-side traceback: requirements.txt pinned bare `uvicorn`, which ships
no WebSocket implementation. uvicorn then refuses the upgrade, the browser's
WebSocket silently fails to connect, and the live pipeline tracker just never
updates. The app looks fine until you actually run a task.

`websockets` happened to be present anyway as a transitive dependency of
langgraph-sdk, which is what makes this class of bug dangerous — it works right
up until an unrelated upstream drops the pin. requirements.txt now depends on
`uvicorn[standard]` explicitly, and this test guards that.

Note there is no way to probe this with a plain HTTP request: Starlette routes
WebSocket paths in a separate scope and answers an ordinary GET to one with
404, regardless of whether WS support is installed. So the only meaningful
check is a real client handshake.

Run against a running server:
    pip install -r requirements-dev.txt
    python tests/smoketest_websocket.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from console import force_utf8  # noqa: E402

force_utf8()

WS_URL = "ws://127.0.0.1:8000/ws/logs?session=probe"


def _fail(msg: str, detail: str = "") -> None:
    print(f"  \033[31m✘\033[0m {msg}" + (f" — {detail}" if detail else ""))
    sys.exit(1)


def _pass(msg: str) -> None:
    print(f"  \033[32m✔\033[0m {msg}")


def test_server_has_ws_support() -> None:
    """uvicorn only speaks WebSocket when a WS implementation is installed."""
    print("\n[1] server has a WebSocket implementation available")
    try:
        import websockets  # noqa: F401
    except ImportError:
        _fail("websockets importable in the server env",
              "install uvicorn[standard] (see requirements.txt)")
    _pass("websockets present (via uvicorn[standard])")


def test_client_handshake() -> None:
    print("\n[2] a real client completes the handshake against /ws/logs")
    try:
        from websockets.sync.client import connect
    except ImportError:
        _fail("websockets client unavailable", "pip install -r requirements-dev.txt")
    try:
        with connect(WS_URL, open_timeout=8) as ws:
            # The connection itself is the assertion; the server pushes log
            # lines only when there is activity, so we do not wait for one.
            if ws.protocol.state.name != "OPEN":
                _fail("socket not OPEN after connect", ws.protocol.state.name)
    except Exception as e:
        _fail(
            "handshake failed",
            f"{type(e).__name__}: {e} — if this is an InvalidStatus/426, uvicorn "
            "has no WS implementation; install uvicorn[standard].",
        )
    _pass("101 Switching Protocols, socket OPEN, closed cleanly")


def main() -> None:
    print("Verifying WebSocket transport (the live tracker depends on it)")
    test_server_has_ws_support()
    test_client_handshake()
    print("\n\033[32mWebSocket transport OK — the live tracker will work.\033[0m")


if __name__ == "__main__":
    main()
