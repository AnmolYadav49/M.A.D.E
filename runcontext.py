"""Per-request context: the visitor's LLM key and their session id.

Both need to reach graph nodes that are several async frames deep, and neither
can be a module global — the server handles concurrent requests from different
visitors, so a global would mean visitor A's key being used for visitor B's run
and A's logs being delivered to B's browser.

contextvars is the right tool: values set here are visible to everything
awaited downstream in the same task, and isolated between concurrent tasks.

The key is deliberately never written to state, never returned in a response,
and redacted by `SecretRedactingFilter` if it ever reaches a log record.
"""
from __future__ import annotations

import contextvars
import logging
import re

# The visitor's OpenRouter key for the current request. None => fall back to the
# server-side key (non-public deployments only).
current_llm_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_llm_key", default=None
)

# Identifies the browser tab that started this run, so log lines can be routed
# back to only that tab's websocket.
current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_session_id", default=None
)


class SessionStampFilter(logging.Filter):
    """Stamps every LogRecord with the session id of the run that produced it.

    Records emitted outside a request (startup, uvicorn's own access log) get
    session_id=None, which the websocket layer treats as "broadcast to all" —
    those lines contain no user content.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = current_session_id.get()
        return True


# Matches OpenRouter / OpenAI style keys. Belt and braces: nothing should ever
# put a key in a log line, but if it happens the value must not reach a browser.
_KEY_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9\-_]{8,})")


class SecretRedactingFilter(logging.Filter):
    """Redacts anything that looks like an API key from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if "sk-" in msg:
            redacted = _KEY_PATTERN.sub(lambda m: m.group(1)[:6] + "…REDACTED", msg)
            record.msg = redacted
            record.args = ()
        return True


def redact(text: str) -> str:
    """Redact key-shaped substrings from arbitrary text (e.g. error bodies)."""
    if not text or "sk-" not in text:
        return text
    return _KEY_PATTERN.sub(lambda m: m.group(1)[:6] + "…REDACTED", text)
