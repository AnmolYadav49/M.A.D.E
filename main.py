import os
import re
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
from pydantic import BaseModel
from dotenv import load_dotenv

from graph import made_app
from security import analyze_code, strip_markdown_code_fence, BLOCK as SECURITY_BLOCK

load_dotenv()

app = FastAPI(
    title="M.A.D.E. API",
    description="Multi-Agent Data Engine with HITL Guardrails",
    version="1.1",
)

# --- SECURITY CONFIG ----------------------------------------------------------
# API_KEY: if unset, the server starts in DEV MODE with a loud warning and every
# authenticated route is open. In production, set MADE_API_KEY to a long random
# string and configure clients to send it as `X-API-Key: <key>`.
API_KEY = os.getenv("MADE_API_KEY", "").strip() or None

# CORS: default to same-origin + the Vite dev server. Deployments override with
# MADE_ALLOWED_ORIGINS as a comma-separated list. `*` is not allowed here —
# `Access-Control-Allow-Origin: *` on a route that mutates state is the
# classic self-inflicted CSRF vulnerability.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000,http://localhost:8000"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("MADE_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

# Rate limiting: token bucket per (route, client-IP). Cheap in-memory guard,
# not durable across restarts — a Redis-backed limiter belongs in production.
RATE_LIMIT_PER_MIN = int(os.getenv("MADE_RATE_LIMIT_PER_MIN", "12"))


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# --- AUTH DEPENDENCY ----------------------------------------------------------
async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if API_KEY is None:
        return  # dev mode
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")


# --- RATE LIMITER MIDDLEWARE --------------------------------------------------
_rate_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_RATE_LIMITED_PATHS = {"/execute-task", "/approve-and-run", "/reject-task"}


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if request.url.path in _RATE_LIMITED_PATHS:
        ip = request.client.host if request.client else "unknown"
        key = (request.url.path, ip)
        window_start = time.time() - 60
        bucket = _rate_buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_PER_MIN:
            retry_after = int(60 - (time.time() - bucket[0])) + 1
            return JSONResponse(
                {"detail": f"Rate limit exceeded: {RATE_LIMIT_PER_MIN}/min per IP"},
                status_code=429, headers={"Retry-After": str(retry_after)},
            )
        bucket.append(time.time())
    return await call_next(request)


# --- STATIC FRONTEND SETUP ----------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# --- WEBSOCKET LOGGING SETUP --------------------------------------------------
# `log_subscribers` holds one asyncio.Queue per connected websocket client so every
# client gets every line (a single shared queue would round-robin lines across
# clients instead of broadcasting them, starving whichever client didn't win the
# race to `.get()` it).
log_subscribers: set = set()


def broadcast_log(message: str) -> None:
    for queue in list(log_subscribers):
        try:
            queue.put_nowait(message)
        except Exception:
            pass


class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        try:
            broadcast_log(self.format(record))
        except Exception:
            pass


class WebSocketStream:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, message):
        self.original_stream.write(message)
        if message.strip():
            try:
                broadcast_log(message.strip())
            except Exception:
                pass

    def flush(self):
        self.original_stream.flush()


@app.on_event("startup")
async def startup_event():
    sys.stdout = WebSocketStream(sys.stdout)

    ws_handler = WebSocketLogHandler()
    ws_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logging.getLogger("uvicorn.access").addHandler(ws_handler)
    logging.getLogger("uvicorn.error").addHandler(ws_handler)
    logging.getLogger().addHandler(ws_handler)
    logging.getLogger().setLevel(logging.INFO)

    if API_KEY is None:
        logging.warning("=" * 70)
        logging.warning("MADE_API_KEY is UNSET — server started in DEV MODE.")
        logging.warning("All pipeline endpoints are open. Do NOT expose this port to the internet.")
        logging.warning("Set MADE_API_KEY=<long-random-string> before deploying.")
        logging.warning("=" * 70)
    else:
        logging.info("MADE API key auth ENABLED. Allowed origins: %s", ALLOWED_ORIGINS)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    log_subscribers.add(queue)
    try:
        while True:
            log_message = await queue.get()
            await websocket.send_text(log_message)
    except WebSocketDisconnect:
        pass
    finally:
        log_subscribers.discard(queue)


# --- SCHEMAS ------------------------------------------------------------------
class TaskRequest(BaseModel):
    task: str


class ApprovalRequest(BaseModel):
    proposed_code: str
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
    return {
        "status": "M.A.D.E. Core is online.",
        "auth_enabled": API_KEY is not None,
        "allowed_origins": ALLOWED_ORIGINS,
        "rate_limit_per_min": RATE_LIMIT_PER_MIN,
    }


# --- PIPELINE ENDPOINTS -------------------------------------------------------
@app.post("/execute-task")
async def execute_task(request: TaskRequest, _: None = Depends(require_api_key)):
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
        }

        final_state = await made_app.ainvoke(initial_state)

        prior_code = final_state.get("prior_code")
        return {
            "status": "Execution paused. Awaiting human approval." if final_state.get("failure_class") is None else "Pipeline terminated without approval.",
            "reviewer_security_report": final_state.get("reviewer_notes", ""),
            "proposed_code": final_state.get("generated_code", ""),
            "self_healed": bool(prior_code),
            "prior_code": prior_code,
            "heal_error": final_state.get("heal_error"),
            "heal_attempts": final_state.get("heal_attempts", 0),
            "failure_class": final_state.get("failure_class"),
            "security_audit": final_state.get("security_audit"),
            "research_sources": final_state.get("research_sources", []),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve-and-run")
async def approve_and_run(request: ApprovalRequest, _: None = Depends(require_api_key)):
    if not request.human_approved:
        return {"status": "Execution aborted by user."}

    # Second, non-bypassable pass of the AST audit. A tampered client cannot
    # sneak past the reviewer's BLOCK by POSTing forged proposed_code directly:
    # every path that eventually runs code goes through this same check.
    clean_code = strip_markdown_code_fence(request.proposed_code)
    audit = analyze_code(clean_code)
    if audit.is_blocked:
        return {
            "status": "Execution refused by policy",
            "stderr": "AST audit blocked the submitted code at the /approve-and-run gate.",
            "security_audit": audit.to_dict(),
        }

    workspace_dir = "generated_workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    file_path = os.path.join(workspace_dir, "executed_script.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(clean_code)

    try:
        # sys.executable rather than a bare "python" so the sandbox subprocess
        # inherits the same interpreter (and therefore the same installed
        # libraries) as the FastAPI server — otherwise `import numpy/sympy/…`
        # can fail with ModuleNotFoundError depending on how the server was
        # launched (venv vs system Python).
        result = subprocess.run(
            [sys.executable, file_path], capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return {"status": "Execution Successful", "stdout": result.stdout, "security_audit": audit.to_dict()}
        return {"status": "Execution Failed", "stderr": result.stderr, "security_audit": audit.to_dict()}
    except subprocess.TimeoutExpired:
        return {"status": "Failed", "stderr": "Execution timed out. Potential infinite loop.", "security_audit": audit.to_dict()}


@app.post("/reject-task")
async def reject_task(request: RejectRequest = RejectRequest(), _: None = Depends(require_api_key)):
    workspace_dir = "generated_workspace"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    return {"status": "Pipeline rejected and session cleared."}
