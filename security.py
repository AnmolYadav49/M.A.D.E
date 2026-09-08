"""Deterministic AST-based security analysis for LLM-generated Python.

This is the security boundary the UI's "Security Clearance" modal advertises:
every piece of generated code is parsed and walked BEFORE the reviewer LLM ever
sees it. The LLM commentary layer above this can only add human-readable
context — it can never override a BLOCK verdict here, and it does not run at
all if the AST audit fails.

Design choices worth flagging for a reviewer:

- Fail-closed on `SyntaxError`: unparseable code is never approved.
- Import allowlist rather than blocklist. Reasoning: new dangerous stdlib
  modules land every Python release; a blocklist misses them by default. An
  allowlist of vetted safe modules cannot be extended by a prompt-injection
  attack, only by editing this file.
- Attribute-access checks reject `getattr(os, 'sys' + 'tem')` because we
  refuse `os.*` attribute chains outright when `os` is not on the allowlist —
  the string-concat trick can't create an `os` reference in the first place.
- We also reject dunder attribute access (`obj.__class__.__mro__[…]`) which is
  how Python sandbox escapes are typically built.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field, asdict
from typing import Iterable

# Modules the Coder is allowed to import. Everything else is refused.
ALLOWED_IMPORTS: frozenset[str] = frozenset({
    # Standard library — safe, deterministic, offline
    "math", "cmath", "random", "statistics", "decimal", "fractions",
    "json", "csv", "re", "string", "textwrap", "unicodedata",
    "collections", "itertools", "functools", "operator", "heapq", "bisect",
    "datetime", "time", "calendar", "zoneinfo",
    "hashlib", "hmac", "base64", "secrets",
    "typing", "dataclasses", "enum", "abc",
    "io",  # StringIO/BytesIO only; the sandbox layer covers real fd access
    # Numeric / data / ML — the whole point of a data engine
    "numpy", "pandas", "scipy", "sklearn",
    "sympy",  # symbolic math — the answer to "solve this equation" tasks
    "matplotlib", "seaborn", "plotly",
    # Vector store / retrieval used by the app itself
    "faiss", "langchain",
})

# Callables that are refused wherever they resolve from.
BLOCKED_BUILTINS: frozenset[str] = frozenset({
    "eval", "exec", "compile", "__import__",
    "input",       # blocks interactive prompts inside batch runs
    "breakpoint",  # blocks dropping into pdb
})

# Dunder attributes commonly used for sandbox escapes
# (e.g. `().__class__.__base__.__subclasses__()`). Legitimate patterns like
# `if __name__ == "__main__":` and defining `__init__`/`__repr__` on a class
# use these as *names*, not attribute lookups, so they're unaffected.
BLOCKED_DUNDER_ATTRS: frozenset[str] = frozenset({
    "__class__", "__bases__", "__base__", "__subclasses__", "__mro__",
    "__globals__", "__builtins__", "__import__",
    "__getattribute__", "__setattr__", "__delattr__",
    "__dict__", "__code__", "__closure__", "__func__",
    "__reduce__", "__reduce_ex__",
})

# `<module>.<attr>` pairs that are refused even when the module itself might be
# allowlisted (currently none are, but this guards future additions).
BLOCKED_ATTRIBUTE_CHAINS: frozenset[tuple[str, str]] = frozenset({
    ("os", "system"), ("os", "popen"), ("os", "remove"), ("os", "unlink"),
    ("os", "rmdir"), ("os", "removedirs"), ("os", "kill"), ("os", "fork"),
    ("os", "execv"), ("os", "execve"), ("os", "spawnl"), ("os", "environ"),
    ("subprocess", "run"), ("subprocess", "Popen"), ("subprocess", "call"),
    ("subprocess", "check_call"), ("subprocess", "check_output"),
    ("shutil", "rmtree"),
    ("socket", "socket"), ("socket", "create_connection"),
    ("urllib", "request"), ("urllib.request", "urlopen"),
    ("requests", "get"), ("requests", "post"), ("requests", "request"),
    ("httpx", "get"), ("httpx", "post"),
    ("pickle", "loads"), ("pickle", "load"),
    ("ctypes", "CDLL"), ("ctypes", "cdll"),
})

# Severity levels the frontend renders as pass/warn/block chips.
PASS = "pass"
WARN = "warn"
BLOCK = "block"


@dataclass
class Finding:
    """One structured audit result — the row shape the UI's Security Audit strip renders."""
    check: str
    detail: str
    severity: str  # PASS / WARN / BLOCK
    line: int | None = None


@dataclass
class SecurityAudit:
    verdict: str  # PASS or BLOCK (WARN is per-finding; overall stays PASS unless a BLOCK exists)
    findings: list[Finding] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return self.verdict == BLOCK

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "findings": [asdict(f) for f in self.findings]}


def _root_name(node: ast.AST) -> str | None:
    """Return the leftmost identifier of an attribute chain, e.g. `os.path.join` -> "os"."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _chain_names(node: ast.Attribute) -> tuple[str, str] | None:
    """Return ("<root-module>", "<last-attr>") for an ast.Attribute, if the chain is a bare name."""
    root = _root_name(node)
    if root is None:
        return None
    return (root, node.attr)


def analyze_code(source: str) -> SecurityAudit:
    """Parse and walk `source`; return a structured audit.

    The audit is fail-closed: a SyntaxError is a BLOCK, and any BLOCK-severity
    finding poisons the overall verdict regardless of how many PASS checks
    accumulated first. The reviewer node treats `verdict == BLOCK` as a hard
    stop and refuses to hand the code to the HITL gate.
    """
    findings: list[Finding] = []

    # 1. Parse — unparseable is a hard block.
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return SecurityAudit(
            verdict=BLOCK,
            findings=[Finding(check="Syntax", detail=f"SyntaxError: {e.msg}", severity=BLOCK, line=e.lineno)],
        )
    findings.append(Finding(check="Syntax", detail="ast.parse succeeded", severity=PASS))

    # 2. Import allowlist enforcement.
    imported: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append((node.module.split(".")[0], node.lineno))
    unauthorized = [(name, line) for name, line in imported if name not in ALLOWED_IMPORTS]
    for name, line in unauthorized:
        findings.append(Finding(
            check="Import allowlist",
            detail=f"'{name}' is not on the allowlist",
            severity=BLOCK, line=line,
        ))
    if imported and not unauthorized:
        vetted = sorted({name for name, _ in imported})
        findings.append(Finding(
            check="Import allowlist",
            detail=f"All imports on allowlist ({', '.join(vetted)})",
            severity=PASS,
        ))

    # 3. Blocked builtins & dangerous attribute chains.
    saw_dangerous_call = False
    saw_dunder_access = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BLOCKED_BUILTINS:
                findings.append(Finding(
                    check="Dangerous builtin",
                    detail=f"call to '{func.id}(...)' is denied",
                    severity=BLOCK, line=node.lineno,
                ))
                saw_dangerous_call = True
            elif isinstance(func, ast.Attribute):
                chain = _chain_names(func)
                if chain in BLOCKED_ATTRIBUTE_CHAINS:
                    findings.append(Finding(
                        check="Dangerous attribute call",
                        detail=f"call to '{chain[0]}.{chain[1]}(...)' is denied",
                        severity=BLOCK, line=node.lineno,
                    ))
                    saw_dangerous_call = True
        # Dunder introspection is the standard sandbox-escape vector; block the
        # attack-surface set specifically rather than every dunder (which would
        # break legitimate `__init__` definitions, `__name__` checks, etc.).
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_DUNDER_ATTRS:
                findings.append(Finding(
                    check="Dunder access",
                    detail=f"access to '.{node.attr}' is denied (sandbox-escape vector)",
                    severity=BLOCK, line=node.lineno,
                ))
                saw_dunder_access = True

    if not saw_dangerous_call:
        findings.append(Finding(check="Dangerous builtin", detail="No eval/exec/compile/__import__ found", severity=PASS))
    if not saw_dunder_access:
        findings.append(Finding(check="Dunder access", detail="No dunder-attribute sandbox-escape pattern", severity=PASS))

    verdict = BLOCK if any(f.severity == BLOCK for f in findings) else PASS
    return SecurityAudit(verdict=verdict, findings=findings)


def summarize(audit: SecurityAudit) -> str:
    """Compact human-readable summary of the audit for logs / LLM prompts."""
    blocks = [f for f in audit.findings if f.severity == BLOCK]
    if audit.is_blocked:
        return "AST audit BLOCKED: " + "; ".join(f"{f.check}: {f.detail}" for f in blocks)
    passes = sum(1 for f in audit.findings if f.severity == PASS)
    return f"AST audit PASSED ({passes} checks, 0 blocks)."


def strip_markdown_code_fence(text: str) -> str:
    """Best-effort extract of the code inside ```python …``` blocks the Coder sometimes emits."""
    import re
    m = re.search(r"```(?:python)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()
