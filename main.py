import os
import re
import shutil
import subprocess
import logging
import asyncio
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import the compiled state machine from your graph file
from graph import made_app

load_dotenv()

app = FastAPI(
    title="M.A.D.E. API", 
    description="Multi-Agent Data Engine with HITL Guardrails",
    version="1.0"
)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FRONTEND SETUP ---
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# --- WEBSOCKET LOGGING SETUP ---
log_queue = None

class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        if log_queue is not None:
            try:
                log_queue.put_nowait(self.format(record))
            except Exception:
                pass

class WebSocketStream:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, message):
        # 1. Print to the normal VS Code terminal
        self.original_stream.write(message)
        
        # 2. Clone it to the WebSocket queue
        if message.strip() and log_queue is not None:
            try:
                # Prefix with [AGENT] for styling, or leave as raw message
                log_queue.put_nowait(message.strip())
            except Exception:
                pass

    def flush(self):
        self.original_stream.flush()

@app.on_event("startup")
async def startup_event():
    global log_queue
    log_queue = asyncio.Queue()
    
    # Hijack sys.stdout to mirror print statements to WebSocket
    sys.stdout = WebSocketStream(sys.stdout)
    
    ws_handler = WebSocketLogHandler()
    ws_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    
    # Hijack Uvicorn's internal loggers and the root logger
    logging.getLogger("uvicorn.access").addHandler(ws_handler)
    logging.getLogger("uvicorn.error").addHandler(ws_handler)
    logging.getLogger().addHandler(ws_handler)
    logging.getLogger().setLevel(logging.INFO)
    sys.stdout = WebSocketStream(sys.stdout)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if log_queue is not None:
                log_message = await log_queue.get()
                await websocket.send_text(log_message)
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass


# --- SCHEMAS ---
class TaskRequest(BaseModel):
    task: str

class ApprovalRequest(BaseModel):
    proposed_code: str
    human_approved: bool

class RejectRequest(BaseModel):
    session_id: Optional[str] = "default"


# --- FRONTEND & HEALTH ENDPOINTS ---
@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "M.A.D.E. Core is online. Frontend index.html not found in /frontend."}

@app.get("/api/health")
async def health_check():
    return {"status": "M.A.D.E. Core is online."}


# --- PIPELINE ENDPOINTS ---
@app.post("/execute-task")
async def execute_task(request: TaskRequest):
    try:
        # Initialize the DFA state tape
        initial_state = {
            "task": request.task,
            "research_context": "",
            "generated_code": "",
            "reviewer_notes": "",
            "human_approved": False,
            "error_traceback": None,
            "execution_output": None
        }
        
        # Trigger the Graph Asynchronously
        final_state = await made_app.ainvoke(initial_state)
        
        # Return the payload to the user for HITL approval
        return {
            "status": "Execution paused. Awaiting human approval.",
            "reviewer_security_report": final_state["reviewer_notes"],
            "proposed_code": final_state["generated_code"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve-and-run")
async def approve_and_run(request: ApprovalRequest):
    # The HITL Gate Check
    if not request.human_approved:
        return {"status": "Execution aborted by user."}
    
    # Create a workspace directory for generated scripts
    workspace_dir = "generated_workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    file_path = os.path.join(workspace_dir, "executed_script.py")
    
    # Extract only the code inside the markdown block
    match = re.search(r'```(?:python)?(.*?)```', request.proposed_code, re.DOTALL | re.IGNORECASE)
    
    if match:
        clean_code = match.group(1).strip()
    else:
        # Fallback: if the LLM didn't use backticks, just strip whitespace
        clean_code = request.proposed_code.strip()
    
    # Write the approved code to disk
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(clean_code)
        
    # Execute the script in a safe subprocess
    try:
        result = subprocess.run(
            ["python", file_path],
            capture_output=True,
            text=True,
            timeout=15 
        )
        
        if result.returncode == 0:
            return {
                "status": "Execution Successful",
                "stdout": result.stdout
            }
        else:
            return {
                "status": "Execution Failed",
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {"status": "Failed", "stderr": "Execution timed out. Potential infinite loop."}

@app.post("/reject-task")
async def reject_task(request: RejectRequest = RejectRequest()):
    # Securely delete the temporary workspace directory
    workspace_dir = "generated_workspace"
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir, ignore_errors=True)
    return {"status": "Pipeline rejected and session cleared."}