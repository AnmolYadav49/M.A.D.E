"""Deployment configuration for M.A.D.E.

The important idea here is that "runs on my laptop" and "runs on a public URL
that strangers can POST to" are different threat models, and the code should
not silently treat them the same.

Local / trusted:   MADE_PUBLIC_MODE=0, execution ON, server-side key.
Public deployment: MADE_PUBLIC_MODE=1, execution OFF by default, visitors bring
                   their own OpenRouter key.

The execution default flips with public mode deliberately. The static AST audit
is defence in depth, not a sandbox: an allowlisted library with a string-eval
API (sympy.sympify, pandas.eval) is arbitrary code execution, and those are
blocked only because they were found and named. Assuming the list is now
complete would be the same mistake again. So on a public deployment the
sandbox does not run untrusted code unless an operator explicitly opts in with
MADE_ALLOW_EXECUTION=1 and has read the README's threat-model section.
"""
from __future__ import annotations

import os


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- deployment posture -------------------------------------------------------
PUBLIC_MODE: bool = _flag("MADE_PUBLIC_MODE", False)
"""Public mode: visitors supply their own OpenRouter key per request."""

ALLOW_EXECUTION: bool = _flag("MADE_ALLOW_EXECUTION", not PUBLIC_MODE)
"""Whether the sandbox node may actually run generated code.

Defaults OFF in public mode. With it off the whole pipeline still runs —
research, code synthesis, the policy audit, the reviewer and the HITL gate —
so the demo is intact; only the subprocess execution step is skipped.
"""

DEMO_MODE: bool = _flag("MADE_DEMO_MODE", False)

# --- auth ---------------------------------------------------------------------
SERVER_API_KEY: str | None = (os.getenv("MADE_API_KEY", "").strip() or None)
"""Shared secret for the pipeline endpoints. Ignored in public mode, where the
visitor's own LLM key is what gates usage instead."""

SERVER_OPENROUTER_KEY: str | None = (os.getenv("OPENROUTER_API_KEY", "").strip() or None)
"""Fallback LLM key used only when NOT in public mode."""

# --- limits -------------------------------------------------------------------
RATE_LIMIT_PER_MIN: int = int(os.getenv("MADE_RATE_LIMIT_PER_MIN", "12"))
MAX_TASK_CHARS: int = int(os.getenv("MADE_MAX_TASK_CHARS", "2000"))
MAX_HEAL_ATTEMPTS: int = int(os.getenv("MADE_MAX_HEAL_ATTEMPTS", "3"))
SANDBOX_TIMEOUT_SEC: int = int(os.getenv("MADE_SANDBOX_TIMEOUT_SEC", "10"))
SANDBOX_MEM_MB: int = int(os.getenv("MADE_SANDBOX_MEM_MB", "512"))
SANDBOX_MAX_OUTPUT_BYTES: int = int(os.getenv("MADE_SANDBOX_MAX_OUTPUT_BYTES", "64000"))

# --- model / retrieval --------------------------------------------------------
MODEL_NAME: str = os.getenv("MADE_MODEL_NAME", "openrouter/free")
OPENROUTER_BASE_URL: str = os.getenv("MADE_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
FAISS_INDEX_DIR: str = os.getenv("MADE_FAISS_INDEX_DIR", "faiss_index")
RESEARCH_TOP_K: int = int(os.getenv("MADE_RESEARCH_TOP_K", "4"))

# --- CORS ---------------------------------------------------------------------
_DEFAULT_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://127.0.0.1:8000,http://localhost:8000"
)
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("MADE_ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]


def public_health() -> dict:
    """Non-secret description of this deployment, for /api/health and the UI."""
    return {
        "public_mode": PUBLIC_MODE,
        "byok_required": PUBLIC_MODE,
        "execution_enabled": ALLOW_EXECUTION,
        "demo_mode": DEMO_MODE,
        "auth_enabled": SERVER_API_KEY is not None and not PUBLIC_MODE,
        "rate_limit_per_min": RATE_LIMIT_PER_MIN,
        "max_task_chars": MAX_TASK_CHARS,
        "max_heal_attempts": MAX_HEAL_ATTEMPTS,
        "model": MODEL_NAME,
    }
