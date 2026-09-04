from typing import TypedDict, Optional

class MADEState(TypedDict):
    task: str 
    research_context: str 
    generated_code: str 
    reviewer_notes: str 
    human_approved: bool 
    error_traceback: Optional[str]
    execution_output: Optional[str] 