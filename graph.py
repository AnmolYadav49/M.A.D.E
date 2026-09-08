import os
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
    print("--- 🔍 RESEARCHER AGENT ACTIVE ---")
    
    prompt = f"You are a Senior Data Science Researcher. Outline the exact Python libraries and methodology needed to solve this task: {state['task']} Keep it concise."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"research_context": response.content} 

def coder_node(state: MADEState):
    print("--- 💻 CODER AGENT ACTIVE ---")
    prompt = f"You are an Expert Python Developer. Write the code for this task: {state['task']}. \n\nUse this methodology: {state['research_context']}. \n\nReturn ONLY raw, valid Python code. No markdown formatting."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"generated_code": response.content} 
def reviewer_node(state: MADEState):
    print("--- 🛡️ REVIEWER AGENT ACTIVE ---")
    prompt = f"You are a strict Security & Code Reviewer. Review this code: \n\n{state['generated_code']}\n\nCheck for syntax errors, missing imports, or dangerous commands. Provide a brief security clearance report."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"reviewer_notes": response.content, "human_approved": False} 


workflow = StateGraph(MADEState)


workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("reviewer", reviewer_node)


workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "coder")
workflow.add_edge("coder", "reviewer")
workflow.add_edge("reviewer", END) 


made_app = workflow.compile()