"""M.A.D.E. multi-agent graph — Researcher → Coder → Sandbox → Reviewer → END.

Extensions over the demo baseline (all in service of "no judge questions the logic"):

- Researcher grounds its methodology in a FAISS retrieval over a curated corpus
  (see build_db.py). What snippets it used are stored in state.research_sources
  so the UI can render "grounded in:" citations rather than free-form prose.

- The self-heal loop from Sandbox back to Coder is bounded (MAX_HEAL_ATTEMPTS,
  default 3). Beyond the cap the graph terminates cleanly with a failure_class
  of "exhausted" — no more silent forever-spins on a bad LLM day.

- Sandbox failures are classified into syntax / import / timeout / oom /
  runtime, and the Coder re-prompt is tuned per class rather than one generic
  "here's the traceback, try again".

- The Reviewer's *deterministic* first pass is a real AST security audit
  (security.analyze_code). Its verdict is authoritative: an LLM commentary
  layer runs afterwards for prose only and cannot override a BLOCK. If the
  audit blocks, the graph ends with failure_class="policy".
"""
from __future__ import annotations

import logging
import os
import re
import resource
import subprocess
import sys
import tempfile
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

import config
from runcontext import current_llm_key, redact
from state import MADEState
from security import (
    analyze_code, summarize as security_summarize, strip_markdown_code_fence,
    BLOCK as SECURITY_BLOCK,
)

load_dotenv()

MAX_HEAL_ATTEMPTS = config.MAX_HEAL_ATTEMPTS
SANDBOX_TIMEOUT_SEC = config.SANDBOX_TIMEOUT_SEC
FAISS_INDEX_DIR = config.FAISS_INDEX_DIR
RESEARCH_TOP_K = config.RESEARCH_TOP_K
DEMO_MODE = config.DEMO_MODE


_demo_llm = None


class MissingLLMKey(RuntimeError):
    """Raised when a run has no usable LLM key (public mode, no BYOK header)."""


def llm():
    """Return the chat model for the *current request*.

    In public mode each visitor supplies their own OpenRouter key, so this
    cannot be a module-level singleton — one client per request, built from the
    key in the request context. The key is read from a contextvar rather than
    passed down through every node signature, and is never written into graph
    state (which is serialised into the API response).

    Under MADE_DEMO_MODE the model is replaced by a scripted responder (see
    demo_llm.py). Only the model's *text* is scripted — the graph routing,
    sandbox, AST audit and self-heal loop all still run for real.
    """
    global _demo_llm
    if DEMO_MODE:
        if _demo_llm is None:
            from demo_llm import ScriptedLLM
            logging.warning("--- 🎬 DEMO MODE: using scripted agent responses, NOT live inference ---")
            _demo_llm = ScriptedLLM()
        return _demo_llm

    key = current_llm_key.get() or (None if config.PUBLIC_MODE else config.SERVER_OPENROUTER_KEY)
    if not key:
        raise MissingLLMKey(
            "No LLM key for this request. This deployment runs in public mode, "
            "so each visitor must supply their own OpenRouter key."
        )
    return ChatOpenAI(
        openai_api_base=config.OPENROUTER_BASE_URL,
        openai_api_key=key,
        model_name=config.MODEL_NAME,
        timeout=90,
        max_retries=1,
    )


# --------------------------- Researcher (RAG) ---------------------------------

_retriever = None
_retriever_error: str | None = None


def _load_retriever():
    """Lazy-load the FAISS index once per process; cache the retriever or the reason it failed."""
    global _retriever, _retriever_error
    if _retriever is not None or _retriever_error is not None:
        return _retriever
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_db = FAISS.load_local(FAISS_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
        _retriever = vector_db.as_retriever(search_kwargs={"k": RESEARCH_TOP_K})
        logging.info("--- 📚 RESEARCHER: FAISS index loaded from %s ---", FAISS_INDEX_DIR)
    except Exception as e:
        _retriever_error = f"{type(e).__name__}: {e}"
        logging.warning("--- ⚠️  RESEARCHER: FAISS retrieval unavailable (%s) — falling back to unguided LLM prompt ---", _retriever_error)
    return _retriever


def researcher_node(state: MADEState) -> dict[str, Any]:
    logging.info("--- 🔍 RESEARCHER AGENT: Analyzing prompt and gathering context ---")

    retriever = _load_retriever()
    sources: list[dict[str, Any]] = []
    context_block = ""
    if retriever is not None:
        try:
            docs = retriever.invoke(state["task"])
            for d in docs:
                sources.append({
                    "title": d.metadata.get("title", "(untitled)"),
                    "snippet": d.page_content,
                })
            if sources:
                context_block = "Relevant methodology notes retrieved from the local knowledge base:\n\n" + \
                                "\n".join(f"- {s['title']}: {s['snippet']}" for s in sources) + "\n\n"
                logging.info("--- 📚 RESEARCHER: retrieved %d grounding docs ---", len(sources))
        except Exception as e:
            logging.warning("--- ⚠️  RESEARCHER: retrieval query failed (%s) ---", e)

    prompt = (
        f"You are a Senior Data Science Researcher. {context_block}"
        f"For the task below, outline the Python libraries and methodology to solve it. "
        f"Keep it concise (a short paragraph — no code yet). Prefer the retrieved libraries when they fit.\n\n"
        f"TASK: {state['task']}"
    )
    response = llm().invoke([HumanMessage(content=prompt)])
    return {"research_context": response.content, "research_sources": sources}


# --------------------------- Coder --------------------------------------------

_FAILURE_HINTS = {
    "syntax": "Your previous attempt had a Python SYNTAX error. Be extra careful with colons, parentheses, and indentation. Avoid stray backticks.",
    "import": "Your previous attempt failed with an ImportError. Only import from the allowlisted set (math, statistics, decimal, fractions, json, csv, re, collections, itertools, functools, datetime, hashlib, numpy, pandas, scipy, sklearn, sympy). NEVER use os, sys, subprocess, requests, urllib, socket.",
    "timeout": "Your previous attempt exceeded the sandbox time budget. Reduce work: smaller inputs, vectorize with numpy/pandas, avoid nested Python loops over millions of items.",
    "oom": "Your previous attempt ran out of memory. Stream instead of materializing, reduce batch sizes, avoid np.zeros((10**6, 10**6))-style allocations.",
    "runtime": "Your previous attempt raised a runtime error. Read the traceback carefully, then produce a corrected version.",
    "policy": "Your previous attempt was refused by the AST security audit. You MUST NOT use os, sys, subprocess, eval, exec, compile, __import__, dunder introspection (__class__, __subclasses__, __globals__, __builtins__), or unlisted imports.",
}


def coder_node(state: MADEState) -> dict[str, Any]:
    logging.info("--- 💻 CODER AGENT: Synthesizing Python code ---")

    error_traceback = state.get("error_traceback")
    failure_class = state.get("failure_class") or "runtime"
    attempt = state.get("heal_attempts", 0)

    if error_traceback:
        hint = _FAILURE_HINTS.get(failure_class, _FAILURE_HINTS["runtime"])
        prompt = (
            f"You are an Expert Python Developer working inside a strict sandbox.\n\n"
            f"HINT ({failure_class} · attempt {attempt + 1}/{MAX_HEAL_ATTEMPTS}): {hint}\n\n"
            f"Failure trace from the previous run:\n{error_traceback}\n\n"
            f"Previous code:\n{state.get('generated_code', '')}\n\n"
            f"Original task: {state['task']}\n"
            f"Methodology: {state.get('research_context', '')}\n\n"
            f"Return ONLY raw Python code (no markdown, no prose)."
        )
    else:
        prompt = (
            f"You are an Expert Python Developer working inside a strict sandbox.\n"
            f"Allowed imports: math, statistics, decimal, fractions, json, csv, re, collections, itertools, "
            f"functools, datetime, hashlib, numpy, pandas, scipy, sklearn, sympy, matplotlib. "
            f"No os, sys, subprocess, requests, urllib, socket, ctypes, pickle, or dunder introspection.\n\n"
            f"Write code for this task: {state['task']}\n\n"
            f"Use this methodology: {state.get('research_context', '')}\n\n"
            f"Return ONLY raw Python code (no markdown, no prose)."
        )

    response = llm().invoke([HumanMessage(content=prompt)])

    result: dict[str, Any] = {"generated_code": response.content}
    if error_traceback:
        result["prior_code"] = state.get("generated_code", "")
        result["heal_error"] = error_traceback
        result["heal_attempts"] = attempt + 1
        # clear the traceback so we don't loop-detect a stale failure
        result["error_traceback"] = None
    return result


# --------------------------- Sandbox executor ---------------------------------

def _sandbox_rlimits() -> None:
    """Apply hard resource caps in the child, before exec.

    The AST audit cannot be assumed complete — sympy.sympify and pandas.eval
    were each arbitrary code execution through an allowlisted import until they
    were specifically named. These limits bound the blast radius of the next
    such gap rather than relying on having found them all: a bypass gets a
    CPU-seconds budget, an address-space ceiling, no ability to fork, and no
    ability to write a large file.

    Runs in the forked child via preexec_fn, so a failure here kills only that
    child. POSIX only; on platforms without `resource` the caller skips it.
    """
    cpu = max(1, SANDBOX_TIMEOUT_SEC)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    mem = config.SANDBOX_MEM_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        # Blocks fork bombs. Not available everywhere, and harmless if missing.
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except (ValueError, OSError):
        pass


def _preexec():
    return _sandbox_rlimits() if hasattr(resource, "setrlimit") else None


def _truncate(text: str | None) -> str:
    """Clamp captured output so one run cannot flood the log stream or response."""
    if not text:
        return ""
    limit = config.SANDBOX_MAX_OUTPUT_BYTES
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated at {limit} bytes]"


def sandbox_env() -> dict[str, str]:
    """Minimal environment for the sandbox subprocess.

    The child must not inherit the parent's environment: OPENROUTER_API_KEY and
    MADE_API_KEY live there, and anything the generated code can read it can
    also print — straight into the session log rendered in the browser. We pass
    only what CPython needs to start.
    """
    return {
        "PATH": os.getenv("PATH", "/usr/bin:/bin"),
        "LANG": os.getenv("LANG", "C.UTF-8"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        # HOME is deliberately pointed at the throwaway cwd, so `~` expansions
        # cannot reach the operator's real home directory.
        "HOME": ".",
    }


def _classify_failure(returncode: int, stderr: str, timed_out: bool = False) -> str:
    """Bucket a subprocess failure so the Coder gets a targeted repair prompt."""
    if timed_out:
        return "timeout"
    if returncode == -9 or "MemoryError" in stderr:
        return "oom"
    if "SyntaxError" in stderr:
        return "syntax"
    if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
        return "import"
    return "runtime"


def sandbox_executor_node(state: MADEState) -> dict[str, Any]:
    # Execution kill-switch. On a public deployment the default is OFF, because
    # no amount of static analysis makes running a stranger's generated Python
    # on your own host safe. The rest of the pipeline is unaffected: the code
    # has already been written and audited, and the Reviewer and HITL gate
    # still run — only the subprocess is skipped.
    if not config.ALLOW_EXECUTION:
        logging.info("--- ⏸️  SANDBOX SKIPPED: execution disabled on this deployment (MADE_ALLOW_EXECUTION=0) ---")
        return {
            "execution_output": None,
            "error_traceback": None,
            "failure_class": None,
            "execution_skipped": True,
        }

    logging.info("--- ⚡ SANDBOX EXECUTOR: Running isolated test execution ---")
    clean_code = strip_markdown_code_fence(state.get("generated_code", ""))

    try:
        # sys.executable so the sandbox runs with the same interpreter (and
        # therefore the same site-packages) as the graph — see the matching
        # note in main.py's /approve-and-run.
        #
        # cwd is an empty throwaway directory so relative paths the model might
        # emit ('.env', 'mock_data.csv') resolve into nothing rather than into
        # the repo. Combined with sandbox_env() and the rlimits in _preexec,
        # a bypass of the AST audit lands somewhere with no secrets, no project
        # files, a CPU budget and a memory ceiling.
        with tempfile.TemporaryDirectory(prefix="made-sandbox-") as workdir:
            result = subprocess.run(
                [sys.executable, "-I", "-c", clean_code],  # -I: isolated mode, ignores PYTHON* env and cwd on sys.path
                capture_output=True, text=True, timeout=SANDBOX_TIMEOUT_SEC,
                cwd=workdir, env=sandbox_env(), preexec_fn=_preexec,
            )
        if result.returncode == 0:
            logging.info("--- ✅ SANDBOX SUCCESS: Traceback clean. Routing to Reviewer ---")
            return {"execution_output": _truncate(result.stdout), "error_traceback": None, "failure_class": None}
        cls = _classify_failure(result.returncode, result.stderr or "")
        logging.info("--- ❌ SANDBOX FAILED (%s): routing back to Coder for self-healing ---", cls)
        return {"execution_output": None, "error_traceback": _truncate(result.stderr), "failure_class": cls}
    except subprocess.TimeoutExpired:
        logging.info("--- ❌ SANDBOX FAILED (timeout): routing back to Coder for self-healing ---")
        return {"execution_output": None, "error_traceback": f"Execution timed out after {SANDBOX_TIMEOUT_SEC} seconds.", "failure_class": "timeout"}
    except Exception as e:  # subprocess itself blew up, not the child
        logging.info("--- ❌ SANDBOX FAILED (runtime): %s ---", e)
        return {"execution_output": None, "error_traceback": redact(str(e)), "failure_class": "runtime"}


# --------------------------- Policy gate (pre-execution) ----------------------

def audit_node(state: MADEState) -> dict[str, Any]:
    """Static policy gate. Runs BEFORE the sandbox, never after.

    This node exists because of a real ordering defect: the AST audit used to
    live only in reviewer_node, which the graph reaches *after*
    sandbox_executor_node. That meant untrusted generated code was executed
    first and audited second — `os.popen('id')` ran (as root) before anything
    inspected it. A static control positioned downstream of the thing it is
    meant to protect is decoration, not enforcement.

    The audit result is written to state here and reused by reviewer_node, so
    the code is parsed once and the same verdict is reported everywhere.
    """
    logging.info("--- 🔒 POLICY GATE: static AST audit before execution ---")
    clean_code = strip_markdown_code_fence(state.get("generated_code", ""))
    audit = analyze_code(clean_code)

    if audit.is_blocked:
        logging.info("--- 🚫 POLICY GATE: BLOCKED — code will NOT be executed. %s ---",
                     security_summarize(audit))
        return {
            "security_audit": audit.to_dict(),
            "failure_class": "policy",
            "error_traceback": security_summarize(audit),
        }

    logging.info("--- ✅ POLICY GATE: passed, releasing to sandbox ---")
    return {"security_audit": audit.to_dict(), "failure_class": None, "error_traceback": None}


def route_after_audit(state: MADEState) -> str:
    """Blocked code never reaches the sandbox; it goes back to the Coder (capped)."""
    if state.get("failure_class") != "policy":
        return "sandbox_executor"
    if state.get("heal_attempts", 0) >= MAX_HEAL_ATTEMPTS:
        logging.info("--- 🛑 POLICY BLOCK persisted for %d attempts — terminating ---", MAX_HEAL_ATTEMPTS)
        return "blocked"
    logging.info("--- 🔁 POLICY BLOCK: re-routing to Coder to produce compliant code (attempt %d/%d) ---",
                 state.get("heal_attempts", 0) + 1, MAX_HEAL_ATTEMPTS)
    return "coder"


def blocked_node(state: MADEState) -> dict[str, Any]:
    """Terminal node for code the policy gate refused and the Coder could not fix."""
    return {
        "failure_class": "policy",
        "reviewer_notes": (
            "Refused by the static policy gate before execution.\n\n"
            + (state.get("error_traceback") or "")
        ),
        "human_approved": False,
    }


# --------------------------- Reviewer -----------------------------------------

def reviewer_node(state: MADEState) -> dict[str, Any]:
    """LLM commentary on top of the already-passed static audit.

    By the time the graph reaches here the policy gate has already approved the
    code and the sandbox has run it cleanly. The audit verdict is re-read from
    state rather than recomputed, so there is exactly one source of truth.
    """
    logging.info("--- 🛡️  REVIEWER AGENT: syntax + correctness review ---")

    clean_code = strip_markdown_code_fence(state.get("generated_code", ""))
    audit_dict = state.get("security_audit") or analyze_code(clean_code).to_dict()
    audit_summary = (
        f"AST audit PASSED ({sum(1 for f in audit_dict['findings'] if f['severity'] == 'pass')} checks, 0 blocks)."
    )

    prompt = (
        f"You are a strict Security & Code Reviewer. The deterministic AST audit already passed with these checks:\n"
        f"{audit_summary}\n\n"
        f"Review this code for correctness, missing edge cases, and any residual concerns the AST audit cannot see. "
        f"Be brief (3–5 sentences).\n\nCODE:\n{clean_code}"
    )
    try:
        llm_notes = llm().invoke([HumanMessage(content=prompt)]).content
    except Exception as e:
        llm_notes = f"(LLM commentary unavailable: {e})"

    return {
        "security_audit": audit_dict,
        "reviewer_notes": f"{audit_summary}\n\n{llm_notes}",
        "failure_class": None,
        "human_approved": False,
    }


# --------------------------- Routing ------------------------------------------

def route_after_execution(state: MADEState) -> str:
    if state.get("error_traceback") is None:
        logging.info("--- ✅ SANDBOX SUCCESS: Routing to Reviewer ---")
        return "reviewer"
    if state.get("heal_attempts", 0) >= MAX_HEAL_ATTEMPTS:
        logging.info("--- 🛑 HEAL EXHAUSTED after %d attempts — terminating pipeline ---", MAX_HEAL_ATTEMPTS)
        return "exhausted"
    logging.info("--- 🔁 REFLECTION LOOP: Error detected, re-routing to Coder (attempt %d/%d) ---",
                 state.get("heal_attempts", 0) + 1, MAX_HEAL_ATTEMPTS)
    return "coder"


def exhausted_node(state: MADEState) -> dict[str, Any]:
    """Terminal node reached when the self-heal loop hits its retry cap."""
    return {
        "failure_class": "exhausted",
        "reviewer_notes": (
            f"Self-heal exhausted after {MAX_HEAL_ATTEMPTS} attempts. "
            f"Last failure class: {state.get('failure_class')}."
        ),
    }


# --------------------------- Graph wiring -------------------------------------

# researcher → coder → [policy gate] → sandbox → reviewer → END
#                        │                 │
#                        │ blocked         │ failed
#                        └──► coder ◄──────┘   (both capped by MAX_HEAL_ATTEMPTS)
#
# The policy gate sits between coder and sandbox deliberately: generated code is
# audited BEFORE it is ever executed, not after.
workflow = StateGraph(MADEState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("audit", audit_node)
workflow.add_node("sandbox_executor", sandbox_executor_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("exhausted", exhausted_node)
workflow.add_node("blocked", blocked_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "audit")
workflow.add_conditional_edges(
    "audit",
    route_after_audit,
    {"sandbox_executor": "sandbox_executor", "coder": "coder", "blocked": "blocked"},
)
workflow.add_conditional_edges(
    "sandbox_executor",
    route_after_execution,
    {"coder": "coder", "reviewer": "reviewer", "exhausted": "exhausted"},
)
workflow.add_edge("reviewer", END)
workflow.add_edge("exhausted", END)
workflow.add_edge("blocked", END)

made_app = workflow.compile()
