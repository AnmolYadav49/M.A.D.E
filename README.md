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

---

## 🔐 Security & configuration

M.A.D.E. is intentionally hardened so a technical judge can't poke a hole in the
pipeline's logic. What you'd want to set in a real environment:

| env var | default | what it controls |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | *(required)* | the OpenRouter key used by every LLM node |
| `MADE_API_KEY` | *(unset → dev mode)* | client-facing shared secret; requests to `/execute-task`, `/approve-and-run`, `/reject-task` must send it as `X-API-Key`. If unset, the server boots in DEV MODE with a loud warning and no auth. |
| `MADE_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000,http://localhost:8000` | comma-separated CORS allowlist. `*` is refused. |
| `MADE_RATE_LIMIT_PER_MIN` | `12` | token-bucket cap per (route, client IP) |
| `MADE_MAX_HEAL_ATTEMPTS` | `3` | self-heal loop retry cap; beyond this the pipeline terminates with `failure_class="exhausted"` instead of spinning forever |
| `MADE_SANDBOX_TIMEOUT_SEC` | `10` | wall-clock budget for the sandbox subprocess |
| `MADE_MODEL_NAME` | `openrouter/free` | the model the Coder/Researcher/Reviewer use |
| `MADE_FAISS_INDEX_DIR` | `faiss_index` | where `build_db.py` writes the vector store and `graph.researcher_node` reads it |
| `MADE_RESEARCH_TOP_K` | `4` | how many methodology docs the researcher retrieves per task |

### Security posture (what the modal claims — and now actually enforces)

- **AST audit**, in `security.py`, is the real security boundary. Every piece of
  generated code goes through it before either the Reviewer LLM sees it or the
  HITL gate can approve it. It fails-closed on `SyntaxError`, refuses imports
  outside a small allowlist (math, statistics, numpy, pandas, sympy, scipy,
  sklearn, matplotlib, and stdlib safe modules), refuses `eval`/`exec`/`compile`
  /`__import__`, refuses `os.system`/`subprocess.*`/`socket`/`requests` regardless
  of how the module was renamed, and refuses the `__class__.__base__.__subclasses__`
  sandbox-escape family. An LLM commentary layer runs afterwards but **cannot**
  override a BLOCK.
- The same audit runs on the `/approve-and-run` gate, so a tampered client
  cannot POST forged code past the Reviewer.
- `/ws/logs` broadcasts to one queue per connection so concurrent viewers all
  see every line.

### Real RAG

`build_db.py` builds a FAISS index over a curated methodology corpus (pandas,
numpy, sympy, scipy, sklearn recipes) using `all-MiniLM-L6-v2` embeddings.
`researcher_node` retrieves the top-K relevant recipes for each task and
grounds the methodology prompt in them. The retrieved snippets are exposed to
the UI as "grounded in:" citations. Missing index → graceful fallback to an
unguided LLM prompt with a warning.

### First-time setup

```bash
pip install -r requirements.txt
python build_db.py               # builds faiss_index/ (downloads the embedding model once)
cd web && npm install && npm run build && cd ..
export OPENROUTER_API_KEY=…       # your key
export MADE_API_KEY=…             # any long random string; clients send it as X-API-Key
uvicorn main:app --host 127.0.0.1 --port 8000
```

Verify the hardening: `python tests/smoketest_hardening.py` (server must be
running; the test sets `X-API-Key=smoketest-key-987654321`, so export
`MADE_API_KEY=smoketest-key-987654321` in the terminal that runs uvicorn).
