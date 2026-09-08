"""Make console output safe on Windows.

The agent log lines and the test output use box-drawing characters, arrows and
emoji (`--- 🔍 RESEARCHER AGENT ... ---`). A Windows console defaults to the
legacy cp1252 code page, which cannot encode any of them, so:

  * every test script died with UnicodeEncodeError before printing a result,
    which is why they only ran with PYTHONIOENCODING=utf-8 set by hand; and
  * worse, the server's stderr log handler raised inside `logging`, which
    catches the error and prints a full `--- Logging error ---` traceback —
    once per agent step. A live demo would scroll tracebacks instead of the
    pipeline trace.

Rather than requiring an environment variable to be set correctly every time,
entry points call `force_utf8()`, and log handlers are built with
`errors="replace"` so an un-encodable character degrades to `?` instead of
raising. Python 3.15 makes UTF-8 mode the default and this becomes redundant;
until then it is the difference between the app working out of the box on
Windows and not.
"""
from __future__ import annotations

import sys


def force_utf8() -> None:
    """Reconfigure stdout/stderr to UTF-8, replacing anything un-encodable.

    Safe to call more than once, and a no-op where the streams are already
    UTF-8 (Linux, macOS, and Windows with UTF-8 mode enabled). `errors=replace`
    matters as much as the encoding: a redirected stream or an exotic console
    can still refuse a character, and printing `?` beats aborting the run.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue  # already wrapped (e.g. pytest capture) — leave it alone
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # Detached or non-reconfigurable stream; nothing to do, and this
            # must never be the reason a process fails to start.
            pass
