# 🤖 M.A.D.E. — Multi-Agent Data Engine

**M.A.D.E.** is an autonomous multi-agent pipeline built with **LangGraph**, **FastAPI**, and **FAISS**. It uses a graph-based state machine to orchestrate specialized LLM agents for code generation, security auditing, and sandboxed script execution backed by strict **Human-In-The-Loop (HITL)** guardrails.

---

## 🌟 Features

* **Multi-Agent Collaboration**:
  * 🔍 **Researcher Agent**: Formulates Python libraries and technical methodology for given tasks[cite: 3].
  * 💻 **Coder Agent**: Translates research methodology into clean, executable Python code[cite: 3].
  * 🛡️ **Reviewer Agent**: Performs security checks, inspects syntax, and yields audit reports[cite: 3].
* **Human-In-The-Loop (HITL) Gate**: Execution pauses automatically after code review, waiting for explicit user confirmation before touching the local workspace.
* **Sandboxed Execution**: Runs approved code inside a local, isolated workspace (`generated_workspace/`) with a 15-second subprocess timeout to prevent infinite loops[cite: 4].
* **Vector Store Integration**: Built-in FAISS vector database initialization using HuggingFace embeddings (`all-MiniLM-L6-v2`) for local documentation context.

---


---

## 🛠️ Project Structure

```text
.
├── build_db.py         # Initializes and saves the FAISS vector database[cite: 2]
├── graph.py            # LangGraph state graph & agent node definitions[cite: 3]
├── main.py             # FastAPI REST endpoints & subprocess execution engine[cite: 4]
├── state.py            # TypedDict defining the shared agent state tape[cite: 6]
├── requirements.txt    # Python dependencies[cite: 5]
├── .env                # Environment variables (OpenRouter API Keys)
└── faiss_index/        # Local FAISS vector storage folder[cite: 1, 2]
