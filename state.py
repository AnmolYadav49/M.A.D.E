from typing import TypedDict, Optional, List, Dict, Any


class MADEState(TypedDict, total=False):
    task: str
    research_context: str
    generated_code: str
    reviewer_notes: str        # human-readable summary (LLM commentary + AST verdict)
    human_approved: bool
    error_traceback: Optional[str]
    execution_output: Optional[str]

    # self-heal state (populated when re-entering coder after a sandbox failure)
    prior_code: Optional[str]
    heal_error: Optional[str]
    heal_attempts: int              # incremented each time coder is re-invoked
    failure_class: Optional[str]    # syntax | import | timeout | oom | runtime | exhausted | policy | none

    # deterministic AST audit — the security boundary the UI advertises
    security_audit: Optional[Dict[str, Any]]  # {verdict, findings:[...]}, from security.SecurityAudit.to_dict()

    # FAISS retrieval (real RAG) — what documents grounded the Researcher's methodology
    research_sources: List[Dict[str, Any]]    # [{title, snippet, score}, …]

    # True when the sandbox was skipped because MADE_ALLOW_EXECUTION is off
    # (the default on public deployments). Distinguishes "did not run" from
    # "ran and passed", which the UI must not conflate.
    execution_skipped: bool
