import os
import shutil
import subprocess
import logging
import asyncio
import sys
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import config
from console import force_utf8
from runcontext import (
    current_llm_key, current_session_id,
    SessionStampFilter, SecretRedactingFilter, redact,
)

# The agent trace is full of emoji ("--- 🔍 RESEARCHER AGENT ..."). On a cp1252
# Windows console the stderr log handler raises UnicodeEncodeError, which
# `logging` catches and reports as a full "--- Logging error ---" traceback —
# once per agent step. Do this before any handler is attached.
force_utf8()
from graph import made_app, sandbox_env, MissingLLMKey, sandbox_popen_kwargs, _truncate
from security import analyze_code, strip_markdown_code_fence

load_dotenv()

app = FastAPI(
    title="M.A.D.E. API",
    description="Multi-Agent Data Engine with HITL Guardrails",
    version="1.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-OpenRouter-Key", "X-Session-Id"],
)


# --- AUTH ---------------------------------------------------------------------
async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Shared-secret gate for private deployments.

    Skipped in public mode: there, the thing gating usage is that each visitor
    must bring their own LLM key, so a shared server secret would only stop
    them from using the app at all.
    """
    if config.PUBLIC_MODE or config.SERVER_API_KEY is None:
        return
    if not x_api_key or x_api_key != config.SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")


def resolve_llm_key(x_openrouter_key: Optional[str]) -> Optional[str]:
    """Pick the LLM key for this request, preferring the visitor's own.

    The visitor's key is used for the duration of one request and then dropped:
    it is never written to disk, never stored in graph state (which is returned
    to the client), and redacted by SecretRedactingFilter if it ever reaches a
    log record.
    """
    byok = (x_openrouter_key or "").strip()
    if byok:
        return byok
    if config.PUBLIC_MODE:
        return None
    return config.SERVER_OPENROUTER_KEY


# --- RATE LIMITER -------------------------------------------------------------
_rate_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_RATE_LIMITED_PATHS = {"/execute-task", "/approve-and-run", "/reject-task"}


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if request.url.path in _RATE_LIMITED_PATHS:
        # X-Forwarded-For matters behind Render/Vercel's proxy: request.client
        # is the proxy there, so without this every visitor shares one bucket.
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
        key = (request.url.path, ip)
        window_start = time.time() - 60
        bucket = _rate_buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= config.RATE_LIMIT_PER_MIN:
            retry_after = int(60 - (time.time() - bucket[0])) + 1
            return JSONResponse(
                {"detail": f"Rate limit exceeded: {config.RATE_LIMIT_PER_MIN}/min per IP"},
                status_code=429, headers={"Retry-After": str(retry_after)},
            )
        bucket.append(time.time())
    return await call_next(request)


# --- STATIC FRONTEND ----------------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# --- WEBSOCKET LOGGING --------------------------------------------------------
# One queue per connected client, each tagged with the session id that client
# owns. A log record is delivered to a client only when the record's session id
# matches, or when the record has no session (startup/uvicorn lines, which carry
# no user content). Without this scoping every visitor on a public deployment
# would see every other visitor's task text, generated code and output.
class _Subscriber:
    __slots__ = ("queue", "session_id")

    def __init__(self, session_id: Optional[str]) -> None:
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.session_id = session_id


log_subscribers: set[_Subscriber] = set()


def broadcast_log(message: str, session_id: Optional[str]) -> None:
    for sub in list(log_subscribers):
        if session_id is not None and sub.session_id != session_id:
            continue
        try:
            sub.queue.put_nowait(message)
        except asyncio.QueueFull:
            pass  # slow client; drop rather than block the pipeline
        except Exception:
            pass


class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        try:
            broadcast_log(self.format(record), getattr(record, "session_id", None))
        except Exception:
            pass


class WebSocketStream:
    """Mirrors print() to the terminal and to the matching session's socket."""

    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, message):
        self.original_stream.write(message)
        if message.strip():
            try:
                broadcast_log(redact(message.strip()), current_session_id.get())
            except Exception:
                pass

    def flush(self):
        self.original_stream.flush()


@app.on_event("startup")
async def startup_event():
    sys.stdout = WebSocketStream(sys.stdout)

    session_filter = SessionStampFilter()
    redact_filter = SecretRedactingFilter()

    ws_handler = WebSocketLogHandler()
    ws_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    ws_handler.addFilter(redact_filter)
    ws_handler.addFilter(session_filter)

    for name in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).addHandler(ws_handler)

    root = logging.getLogger()
    root.addHandler(ws_handler)
    # Without a stream handler the agent trace exists ONLY on the websocket, so
    # with no browser attached a whole run produces nothing an operator can read
    # afterwards. Mirror it to stderr too.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        # force_utf8() above normally makes this moot, but a redirected or
        # non-reconfigurable stream can still refuse a character. Belt and
        # braces: degrade to '?' rather than let a log line take down the
        # handler and print a traceback for every agent step.
        stream = getattr(sys, "stderr", None)
        if stream is not None and getattr(stream, "errors", None) not in (None, "replace", "backslashreplace"):
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError, OSError):
                pass
        stream_handler = logging.StreamHandler(stream)
        stream_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        stream_handler.addFilter(redact_filter)
        root.addHandler(stream_handler)
    root.addFilter(session_filter)
    root.setLevel(logging.INFO)

    banner = "=" * 72
    logging.info(banner)
    logging.info("M.A.D.E. starting — %s", "PUBLIC MODE (bring your own key)" if config.PUBLIC_MODE else "private deployment")
    logging.info("  code execution : %s", "ENABLED" if config.ALLOW_EXECUTION else "DISABLED (pipeline runs, sandbox skipped)")
    logging.info("  demo mode      : %s", "ON (scripted agent text)" if config.DEMO_MODE else "off")
    logging.info("  rate limit     : %d/min per IP", config.RATE_LIMIT_PER_MIN)
    logging.info("  CORS origins   : %s", ", ".join(config.ALLOWED_ORIGINS))
    if config.PUBLIC_MODE and config.ALLOW_EXECUTION:
        logging.warning("  !! PUBLIC MODE WITH EXECUTION ENABLED !!")
        logging.warning("  Visitor-supplied prompts can cause generated Python to run on this host.")
        logging.warning("  The AST audit is defence in depth, NOT a sandbox. Only do this if the")
        logging.warning("  process is itself isolated (container, non-root, no network egress).")
    if not config.PUBLIC_MODE and config.SERVER_API_KEY is None:
        logging.warning("  MADE_API_KEY unset — pipeline endpoints are OPEN. Do not expose this port.")
    logging.info(banner)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket, session: Optional[str] = None):
    await websocket.accept()
    sub = _Subscriber(session_id=session)
    log_subscribers.add(sub)
    try:
        while True:
            message = await sub.queue.get()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        log_subscribers.discard(sub)


# --- SCHEMAS ------------------------------------------------------------------
class TaskRequest(BaseModel):
    task: str = Field(min_length=1, max_length=config.MAX_TASK_CHARS)


class ApprovalRequest(BaseModel):
    proposed_code: str = Field(max_length=200_000)
    human_approved: bool


class RejectRequest(BaseModel):
    session_id: Optional[str] = "default"


# --- FRONTEND & HEALTH --------------------------------------------------------
@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "M.A.D.E. Core is online. Frontend index.html not found in /frontend."}


@app.get("/api/health")
async def health_check():
    """Non-secret description of this deployment, used by the UI to decide
    whether to prompt for a key and whether to warn that execution is off."""
    return {"status": "M.A.D.E. Core is online.", **config.public_health(),
            "allowed_origins": config.ALLOWED_ORIGINS}


# --- PIPELINE -----------------------------------------------------------------
@app.post("/execute-task")
async def execute_task(
    request: TaskRequest,
    _: None = Depends(require_api_key),
    x_openrouter_key: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    llm_key = resolve_llm_key(x_openrouter_key)
    if config.PUBLIC_MODE and not llm_key and not config.DEMO_MODE:
        raise HTTPException(
            status_code=401,
            detail="This deployment runs in public mode. Add your own OpenRouter API key to run the pipeline.",
        )

    # Bind the key and session for everything awaited below. Both are contextvars
    # so concurrent visitors never see each other's key or log lines.
    key_token = current_llm_key.set(llm_key)
    session_token = current_session_id.set(x_session_id)
    try:
        initial_state = {
            "task": request.task,
            "research_context": "",
            "generated_code": "",
            "reviewer_notes": "",
            "human_approved": False,
            "error_traceback": None,
            "execution_output": None,
            "prior_code": None,
            "heal_error": None,
            "heal_attempts": 0,
            "failure_class": None,
            "security_audit": None,
            "research_sources": [],
            "execution_skipped": False,
        }

        final_state = await made_app.ainvoke(initial_state)

        prior_code = final_state.get("prior_code")
        return {
            "status": "Execution paused. Awaiting human approval."
                      if final_state.get("failure_class") is None
                      else "Pipeline terminated without approval.",
            "reviewer_security_report": final_state.get("reviewer_notes", ""),
            "proposed_code": final_state.get("generated_code", ""),
            "self_healed": bool(prior_code),
            "prior_code": prior_code,
            "heal_error": final_state.get("heal_error"),
            "heal_attempts": final_state.get("heal_attempts", 0),
            "failure_class": final_state.get("failure_class"),
            "security_audit": final_state.get("security_audit"),
            "research_sources": final_state.get("research_sources", []),
            "execution_skipped": bool(final_state.get("execution_skipped")),
            "execution_output": final_state.get("execution_output"),
        }

    except MissingLLMKey as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        # redact: provider errors sometimes echo the key back in the message.
        raise HTTPException(status_code=500, detail=redact(str(e)))
    finally:
        current_llm_key.reset(key_token)
        current_session_id.reset(session_token)


@app.post("/approve-and-run")
async def approve_and_run(
    request: ApprovalRequest,
    _: None = Depends(require_api_key),
    x_session_id: Optional[str] = Header(None),
):
    if not request.human_approved:
        return {"status": "Execution aborted by user."}

    if not config.ALLOW_EXECUTION:
        return {
            "status": "Execution disabled",
            "stderr": "Code execution is disabled on this deployment (MADE_ALLOW_EXECUTION=0). "
                      "The pipeline, policy audit and review all ran; only the run step is off.",
            "execution_skipped": True,
        }

    # Second, non-bypassable pass of the AST audit. A tampered client cannot
    # sneak past the policy gate by POSTing forged proposed_code directly:
    # every path that eventually runs code goes through this same check.
    clean_code = strip_markdown_code_fence(request.proposed_code)
    audit = analyze_code(clean_code)
    if audit.is_blocked:
        return {
            "status": "Execution refused by policy",
            "stderr": "AST audit blocked the submitted code at the /approve-and-run gate.",
            "security_audit": audit.to_dict(),
        }

    session_token = current_session_id.set(x_session_id)
    try:
        workspace_dir = "generated_workspace"
        os.makedirs(workspace_dir, exist_ok=True)
        file_path = os.path.join(workspace_dir, "executed_script.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_code)

        try:
            result = subprocess.run(
                [sys.executable, "-I", os.path.basename(file_path)],
                capture_output=True, text=True, timeout=15,
                cwd=workspace_dir, env=sandbox_env(), **sandbox_popen_kwargs(),
            )
            if result.returncode == 0:
                return {"status": "Execution Successful", "stdout": _truncate(result.stdout),
                        "security_audit": audit.to_dict()}
            return {"status": "Execution Failed", "stderr": _truncate(result.stderr),
                    "security_audit": audit.to_dict()}
        except subprocess.TimeoutExpired:
            return {"status": "Failed", "stderr": "Execution timed out. Potential infinite loop.",
                    "security_audit": audit.to_dict()}
    finally:
        current_session_id.reset(session_token)


@app.post("/reject-task")
async def reject_task(request: RejectRequest = RejectRequest(), _: None = Depends(require_api_key)):
    workspace_dir = "generated_workspace"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    return {"status": "Pipeline rejected and session cleared."}
