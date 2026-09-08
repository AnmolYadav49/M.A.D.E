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

### Security posture — what is actually enforced

The **policy gate** (`security.py`, wired as its own LangGraph node) sits
**between the Coder and the Sandbox**, so generated code is audited *before* it
is ever executed. It fails closed on `SyntaxError`, enforces an import
allowlist, refuses `eval`/`exec`/`compile`/`__import__`/`open`, refuses
`os.system`/`subprocess.*`/`socket`/`requests` (resolving import aliases, so
renaming the module does not help), refuses the
`__class__.__base__.__subclasses__` escape family, and refuses the
string-evaluating APIs inside otherwise-allowlisted libraries
(`sympy.sympify`, `pandas.eval`, `DataFrame.query`). The same audit re-runs on
`/approve-and-run`, so a tampered client cannot POST forged code past it.

At runtime the sandbox subprocess additionally gets a **scrubbed environment**
(no API keys inherited), a **throwaway working directory**, `python -I`
isolated mode, and **rlimits** on CPU, address space, file size and process
count.

`tests/test_security_audit.py` covers all of the above; run it after any change
to the allowlists.

> **The honest limitation.** Static analysis of Python is not a sandbox, and
> this one should not be treated as one. Two of the blocks above exist because
> the bypass was found and named: `sympy.sympify("__import__('subprocess')…")`
> returned `root` before it was blocked. There is no reason to believe that
> list is now complete. The audit raises the cost of an attack; the *boundary*
> is the process isolation around it. That is why `MADE_ALLOW_EXECUTION`
> defaults to off on public deployments.

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

---

## 🚀 Deploying

### Use Render, not Vercel

Vercel's Python runtime is serverless, and this backend needs three things it
does not provide:

| requirement | why | Vercel |
| --- | --- | --- |
| WebSockets | the live pipeline tracker is driven by `/ws/logs` | not supported on serverless functions |
| Long requests | `/execute-task` blocks for a whole LangGraph run — several sequential model calls | 10s hobby / 60s pro hard cap |
| Persistent process | the log-subscriber set and rate-limit buckets are in-process state | discarded between invocations |

So the live tracker — the most compelling part of the demo — cannot work on
Vercel without rewriting the transport to polling and splitting the run into
resumable steps. **Render, Fly.io or Railway** all run a normal long-lived
process and are the right shape. `render.yaml` in this repo is a ready
blueprint; `Dockerfile` covers the container path.

You *could* put the frontend on Vercel and point it at a Render backend, but
FastAPI already serves the built frontend, so that only adds a CORS surface.

### Deploy to Render

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select the repo. `render.yaml` is picked up
   automatically.
3. Build the frontend and commit it first (`cd web && npm run build`) — the
   blueprint has no Node step because `frontend/` is tracked.

The blueprint sets `MADE_PUBLIC_MODE=1` and `MADE_ALLOW_EXECUTION=0`, and
deliberately sets **no** `OPENROUTER_API_KEY`: in public mode the server holds
no model credential at all.

### Bring-your-own-key (public mode)

With `MADE_PUBLIC_MODE=1`, visitors supply their own OpenRouter key:

- The UI prompts for it on first load and stores it in **`sessionStorage`**
  (not `localStorage`) so it is dropped when the tab closes.
- It is sent per request as `X-OpenRouter-Key`, held in a `contextvar` for the
  duration of that request, and never written to disk, never put into graph
  state (which is serialised into the response), and never logged.
- `runcontext.SecretRedactingFilter` redacts anything key-shaped from every log
  record and from error bodies, since providers sometimes echo the key back in
  an auth error.
- Each browser tab gets a session id; `/ws/logs` only delivers lines belonging
  to that session. Without this, every visitor would see every other visitor's
  task text, generated code and output.

Verify with `python tests/smoketest_deployment.py` against a running server.

### The threat model, stated plainly

| | execution OFF (default in public mode) | execution ON |
| --- | --- | --- |
| Pipeline runs | yes — research, synthesis, policy audit, review, HITL gate | yes |
| Generated code runs | **no** | yes, in a subprocess |
| Safe on a public URL | yes | **only if the process itself is isolated** |

If you want execution on for a public deployment, do not just flip the flag.
Run the container (`Dockerfile`) with the process as the boundary:

```bash
docker run --rm \
  --network=none \          # no egress from the exec path
  --read-only \             # immutable rootfs
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --memory=512m --cpus=1 --pids-limit=64 \
  --cap-drop=ALL --security-opt=no-new-privileges \
  -e MADE_ALLOW_EXECUTION=1 \
  made-control-center
```

Note `--network=none` conflicts with reaching OpenRouter, so a production
design splits the executor into its own network-isolated worker rather than
running it in the API process. That split is the next real piece of work if
this ever needs to run untrusted code publicly.

### Environment variables added for deployment

| env var | default | what it controls |
| --- | --- | --- |
| `MADE_PUBLIC_MODE` | `0` | visitors bring their own OpenRouter key; disables the shared `X-API-Key` gate |
| `MADE_ALLOW_EXECUTION` | `1` privately, `0` in public mode | whether the sandbox may actually run generated code |
| `MADE_MAX_TASK_CHARS` | `2000` | rejects oversized prompts before any model call is billed |
| `MADE_SANDBOX_MEM_MB` | `512` | `RLIMIT_AS` ceiling for the sandbox child |
| `MADE_SANDBOX_MAX_OUTPUT_BYTES` | `64000` | truncates captured stdout/stderr |

---

## 🪟 Running on Windows

Everything works on Windows, with two caveats worth knowing:

- The sandbox **rlimits** (CPU / memory / process caps) are POSIX-only. On
  Windows the remaining containment is the wall-clock timeout, the scrubbed
  environment and the throwaway working directory. Fine for development;
  deploy on Linux if you ever enable execution publicly.
- Use **PowerShell**. The `set VAR=value` syntax below differs in `cmd.exe`,
  and the commands assume PowerShell throughout.

### One-time setup

```powershell
cd "$env:USERPROFILE\M.A.D.E"

# Python side
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
python build_db.py                 # builds faiss_index\ (downloads the embedding model once)

# Frontend side (needs Node 18+)
cd web
npm install
npm run build
cd ..
```

If `Activate.ps1` is blocked with *"running scripts is disabled on this
system"*, allow local scripts for your user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Run it — demo mode (no API key needed)

```powershell
.\.venv\Scripts\Activate.ps1
$env:MADE_DEMO_MODE = "1"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

### Run it — live agents with your own key

```powershell
.\.venv\Scripts\Activate.ps1
Remove-Item Env:MADE_DEMO_MODE -ErrorAction SilentlyContinue
$env:OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Run it — public / bring-your-own-key mode (what Render runs)

```powershell
.\.venv\Scripts\Activate.ps1
$env:MADE_PUBLIC_MODE = "1"
$env:MADE_ALLOW_EXECUTION = "0"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Tests (second PowerShell window, server already running)

```powershell
cd "$env:USERPROFILE\M.A.D.E"
.\.venv\Scripts\Activate.ps1

python tests\test_security_audit.py      # 39 cases, no server needed
python tests\test_platform_guards.py     # cross-platform guards, no server needed
python tests\smoketest_websocket.py      # needs the server running
python tests\smoketest_deployment.py     # needs the server in MADE_PUBLIC_MODE=1
```

### Clearing an env var between runs

`$env:VAR = "1"` persists for the life of that PowerShell window, which is a
common source of confusion — a server started later in the same window
inherits it. To clear one:

```powershell
Remove-Item Env:MADE_DEMO_MODE -ErrorAction SilentlyContinue
```

Or just open a fresh window.

### cmd.exe equivalents

If you would rather use Command Prompt:

```bat
.venv\Scripts\activate.bat
set MADE_DEMO_MODE=1
set MADE_DEMO_MODE=            :: (clears it — note the trailing =)
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
