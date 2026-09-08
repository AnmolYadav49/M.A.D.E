"""Regression tests for cross-platform sandbox handling.

Three Windows-only failures lived here, none of which reproduce on Linux:

1. `import resource` at module scope. `resource` is POSIX-only, so graph.py —
   and therefore main.py and the entire server — raised ModuleNotFoundError
   on Windows before anything could start.

2. `preexec_fn=` passed to subprocess.run. Windows raises
   `ValueError: preexec_fn is not supported on Windows platforms`, so even a
   no-op callback breaks the sandbox call.

3. A fully scrubbed environment. CPython on Windows cannot start without
   SystemRoot (os.urandom and socket init resolve DLLs relative to it), so
   the hardening that protects secrets on Linux killed the child on Windows.

Run:  python tests/test_platform_guards.py
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import graph  # noqa: E402


def _pass(m): print(f"  \033[32m✔\033[0m {m}")
def _fail(m, d=""): print(f"  \033[31m✘\033[0m {m}" + (f" — {d}" if d else "")); sys.exit(1)


def test_no_preexec_without_resource():
    print("\n[1] no preexec_fn when the resource module is unavailable")
    with patch.object(graph, "resource", None):
        kw = graph.sandbox_popen_kwargs()
    if "preexec_fn" in kw:
        _fail("preexec_fn must be omitted", "would raise ValueError on Windows")
    _pass("omitted")


def test_no_preexec_off_posix():
    print("\n[2] no preexec_fn on a non-POSIX platform")
    with patch.object(graph, "_POSIX", False):
        kw = graph.sandbox_popen_kwargs()
    if "preexec_fn" in kw:
        _fail("preexec_fn must be omitted off POSIX")
    _pass("omitted")


def test_rlimits_still_applied_on_posix():
    print("\n[3] rlimits ARE still applied on POSIX (no regression)")
    if os.name != "posix":
        print("    (not POSIX — skipping)"); _pass("skipped"); return
    kw = graph.sandbox_popen_kwargs()
    if "preexec_fn" not in kw:
        _fail("POSIX must keep its rlimits", "hardening silently lost")
    _pass("preexec_fn present, rlimits intact")


def test_windows_env_is_startable_and_secretless():
    print("\n[4] Windows env keeps SystemRoot but still drops secrets")
    fake = {
        "SystemRoot": r"C:\Windows",
        "COMSPEC": r"C:\Windows\system32\cmd.exe",
        "OPENROUTER_API_KEY": "sk-or-v1-SHOULD-NOT-LEAK",
        "MADE_API_KEY": "SHOULD-NOT-LEAK",
    }
    with patch.dict(os.environ, fake), patch.object(os, "name", "nt"):
        env = graph.sandbox_env()
    if "SystemRoot" not in env:
        _fail("SystemRoot must survive", "child python cannot start without it")
    for leaky in ("OPENROUTER_API_KEY", "MADE_API_KEY"):
        if leaky in env:
            _fail(f"{leaky} must not be inherited")
    _pass("SystemRoot present; no credentials inherited")


def test_posix_env_secretless():
    print("\n[5] POSIX env drops secrets (no regression)")
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-X", "MADE_API_KEY": "Y"}):
        env = graph.sandbox_env()
    for leaky in ("OPENROUTER_API_KEY", "MADE_API_KEY"):
        if leaky in env:
            _fail(f"{leaky} must not be inherited")
    _pass("no credentials inherited")


def main():
    print(f"Platform guards (running on os.name={os.name!r})")
    test_no_preexec_without_resource()
    test_no_preexec_off_posix()
    test_rlimits_still_applied_on_posix()
    test_windows_env_is_startable_and_secretless()
    test_posix_env_secretless()
    print("\n\033[32mPlatform guards OK — imports and runs on Windows and POSIX.\033[0m")


if __name__ == "__main__":
    main()
