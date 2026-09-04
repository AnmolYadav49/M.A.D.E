from typing import TypedDict

class MADEState(TypedDict):
    task: str 
    research_context: str 
    generated_code: str 
    reviewer_notes: str 
    human_approved: bool 