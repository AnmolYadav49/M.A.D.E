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
import subprocess
import sys
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from state import MADEState
from security import (
    analyze_code, summarize as security_summarize, strip_markdown_code_fence,
    BLOCK as SECURITY_BLOCK,
)

load_dotenv()

MAX_HEAL_ATTEMPTS = int(os.getenv("MADE_MAX_HEAL_ATTEMPTS", "3"))
SANDBOX_TIMEOUT_SEC = int(os.getenv("MADE_SANDBOX_TIMEOUT_SEC", "10"))
FAISS_INDEX_DIR = os.getenv("MADE_FAISS_INDEX_DIR", "faiss_index")
RESEARCH_TOP_K = int(os.getenv("MADE_RESEARCH_TOP_K", "4"))


_llm = None


def llm() -> ChatOpenAI:
    """Lazy-init the OpenRouter chat model.

    Module-level construction used to raise at import time when
    OPENROUTER_API_KEY was unset, so `from graph import _load_retriever` (used
    in the smoke test) broke before it could even check the retriever. Deferring
    the check lets non-LLM code paths — the AST audit, the retriever, and tests
    of both — import cleanly.
    """
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            model_name=os.getenv("MADE_MODEL_NAME", "openrouter/free"),
        )
    return _llm


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
    logging.info("--- ⚡ SANDBOX EXECUTOR: Running isolated test execution ---")
    clean_code = strip_markdown_code_fence(state.get("generated_code", ""))

    try:
        # sys.executable so the sandbox runs with the same interpreter (and
        # therefore the same site-packages) as the graph — see the matching
        # note in main.py's /approve-and-run.
        result = subprocess.run(
            [sys.executable, "-c", clean_code],
            capture_output=True, text=True, timeout=SANDBOX_TIMEOUT_SEC,
        )
        if result.returncode == 0:
            logging.info("--- ✅ SANDBOX SUCCESS: Traceback clean. Routing to Reviewer ---")
            return {"execution_output": result.stdout, "error_traceback": None, "failure_class": None}
        cls = _classify_failure(result.returncode, result.stderr or "")
        logging.info("--- ❌ SANDBOX FAILED (%s): routing back to Coder for self-healing ---", cls)
        return {"execution_output": None, "error_traceback": result.stderr, "failure_class": cls}
    except subprocess.TimeoutExpired:
        logging.info("--- ❌ SANDBOX FAILED (timeout): routing back to Coder for self-healing ---")
        return {"execution_output": None, "error_traceback": f"Execution timed out after {SANDBOX_TIMEOUT_SEC} seconds.", "failure_class": "timeout"}
    except Exception as e:  # subprocess itself blew up, not the child
        logging.info("--- ❌ SANDBOX FAILED (runtime): %s ---", e)
        return {"execution_output": None, "error_traceback": str(e), "failure_class": "runtime"}


# --------------------------- Reviewer -----------------------------------------

def reviewer_node(state: MADEState) -> dict[str, Any]:
    """Deterministic AST audit + LLM commentary. Audit is authoritative."""
    logging.info("--- 🛡️  REVIEWER AGENT: AST audit + syntax review ---")

    clean_code = strip_markdown_code_fence(state.get("generated_code", ""))
    audit = analyze_code(clean_code)
    audit_dict = audit.to_dict()

    if audit.is_blocked:
        # Deterministic BLOCK — do NOT ask the LLM. Its verdict does not matter here.
        logging.info("--- 🚫 REVIEWER: BLOCKED by AST audit — refusing to hand off to HITL gate ---")
        return {
            "security_audit": audit_dict,
            "reviewer_notes": security_summarize(audit),
            "failure_class": "policy",
            "human_approved": False,
        }

    # AST audit passed; ask the LLM for a human-readable review as *commentary*.
    prompt = (
        f"You are a strict Security & Code Reviewer. The deterministic AST audit already passed with these checks:\n"
        f"{security_summarize(audit)}\n\n"
        f"Review this code for correctness, missing edge cases, and any residual concerns the AST audit cannot see. "
        f"Be brief (3–5 sentences).\n\nCODE:\n{clean_code}"
    )
    try:
        llm_notes = llm().invoke([HumanMessage(content=prompt)]).content
    except Exception as e:
        llm_notes = f"(LLM commentary unavailable: {e})"

    return {
        "security_audit": audit_dict,
        "reviewer_notes": f"{security_summarize(audit)}\n\n{llm_notes}",
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

workflow = StateGraph(MADEState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("sandbox_executor", sandbox_executor_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("exhausted", exhausted_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "sandbox_executor")
workflow.add_conditional_edges(
    "sandbox_executor",
    route_after_execution,
    {"coder": "coder", "reviewer": "reviewer", "exhausted": "exhausted"},
)
workflow.add_edge("reviewer", END)
workflow.add_edge("exhausted", END)

made_app = workflow.compile()
