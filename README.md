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
├── faiss_index/        # Local FAISS vector storage folder[cite: 1, 2]
├── web/                 # React + Vite source for the control center UI
└── frontend/            # Built UI output (served by main.py) — generated, do not hand-edit
```

---

## 🖥️ Control Center UI

The dashboard is a React app (source in `web/`) built with Vite and served by FastAPI as
static files from `frontend/`. After changing anything under `web/src/`, rebuild:

```bash
cd web
npm install   # first time only
npm run build # writes frontend/index.html + frontend/assets/
```

`main.py` serves `frontend/index.html` at `/` and mounts `frontend/` at `/static` — no
backend changes are needed after a rebuild. For iterative UI work, `npm run dev` inside
`web/` starts a Vite dev server on port 5173 that proxies API/websocket calls to a
FastAPI instance running on `127.0.0.1:8000` (see `web/vite.config.js`).
