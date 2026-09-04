import os
import subprocess
from fastapi import FastAPI, HTTPException
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

# --- SCHEMAS ---
class TaskRequest(BaseModel):
    task: str

class ApprovalRequest(BaseModel):
    proposed_code: str
    human_approved: bool


# --- ENDPOINTS ---
@app.get("/")
async def root():
    return {"status": "M.A.D.E. Core is online."}

@app.post("/execute-task")
async def execute_task(request: TaskRequest):
    try:
        # Initialize the DFA state tape
        initial_state = {
            "task": request.task,
            "research_context": "",
            "generated_code": "",
            "reviewer_notes": "",
            "human_approved": False
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
    
    # Clean the code just in case the LLM returned markdown blocks
    clean_code = request.proposed_code.replace("```python", "").replace("```", "").strip()
    
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