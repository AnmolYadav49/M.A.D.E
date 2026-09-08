import logging
import os
import re
import subprocess
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from state import MADEState

load_dotenv()


llm = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    model_name="openrouter/free", 
)


def researcher_node(state: MADEState):
    logging.info("--- 🔍 RESEARCHER AGENT: Analyzing prompt and gathering context ---")
    
    prompt = f"You are a Senior Data Science Researcher. Outline the exact Python libraries and methodology needed to solve this task: {state['task']} Keep it concise."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"research_context": response.content} 

def coder_node(state: MADEState):
    logging.info("--- 💻 CODER AGENT: Synthesizing Python code ---")
    
    error_traceback = state.get("error_traceback")
    if error_traceback:
        prompt = (
            f"You are an Expert Python Developer.\n"
            f"Your previous code attempt for this task failed with the following error/traceback:\n\n"
            f"{error_traceback}\n\n"
            f"Previous Code:\n{state.get('generated_code', '')}\n\n"
            f"Original Task: {state['task']}\n"
            f"Research Methodology: {state.get('research_context', '')}\n\n"
            f"Please carefully analyze why the previous code failed and provide corrected, working Python code.\n"
            f"Return ONLY raw, valid Python code. No markdown formatting."
        )
    else:
        prompt = (
            f"You are an Expert Python Developer. Write the code for this task: {state['task']}. \n\n"
            f"Use this methodology: {state.get('research_context', '')}. \n\n"
            f"Return ONLY raw, valid Python code. No markdown formatting."
        )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"generated_code": response.content} 

def sandbox_executor_node(state: MADEState):
    logging.info("--- ⚡ SANDBOX EXECUTOR: Running isolated test execution ---")
    raw_code = state.get("generated_code", "")
    
    # Extract only the code inside markdown blocks if present
    match = re.search(r'```(?:python)?(.*?)```', raw_code, re.DOTALL | re.IGNORECASE)
    if match:
        clean_code = match.group(1).strip()
    else:
        clean_code = raw_code.strip()
        
    try:
        result = subprocess.run(
            ["python", "-c", clean_code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logging.info("--- ✅ SANDBOX SUCCESS: Traceback clean. Routing to Reviewer ---")
            return {
                "execution_output": result.stdout,
                "error_traceback": None
            }
        else:
            logging.info("--- ❌ SANDBOX FAILED: Error detected. Routing back to Coder for self-healing ---")
            return {
                "execution_output": None,
                "error_traceback": result.stderr
            }
    except subprocess.TimeoutExpired:
        logging.info("--- ❌ SANDBOX FAILED: Error detected. Routing back to Coder for self-healing ---")
        return {
            "execution_output": None,
            "error_traceback": "Execution timed out after 10 seconds."
        }
    except Exception as e:
        logging.info("--- ❌ SANDBOX FAILED: Error detected. Routing back to Coder for self-healing ---")
        return {
            "execution_output": None,
            "error_traceback": str(e)
        }

def reviewer_node(state: MADEState):
    logging.info("--- 🛡️ REVIEWER AGENT: Performing final security and syntax audit ---")
    prompt = f"You are a strict Security & Code Reviewer. Review this code: \n\n{state['generated_code']}\n\nCheck for syntax errors, missing imports, or dangerous commands. Provide a brief security clearance report."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"reviewer_notes": response.content, "human_approved": False} 


def route_after_execution(state: MADEState):
    if state.get("error_traceback") is not None:
        logging.info("--- 🔁 REFLECTION LOOP: Error detected, re-routing to Coder ---")
        return "coder"
    else:
        logging.info("--- ✅ SANDBOX SUCCESS: Routing to Reviewer ---")
        return "reviewer"


workflow = StateGraph(MADEState)


workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("sandbox_executor", sandbox_executor_node)
workflow.add_node("reviewer", reviewer_node)


workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "sandbox_executor")
workflow.add_conditional_edges(
    "sandbox_executor",
    route_after_execution,
    {
        "coder": "coder",
        "reviewer": "reviewer"
    }
)
workflow.add_edge("reviewer", END) 


made_app = workflow.compile()