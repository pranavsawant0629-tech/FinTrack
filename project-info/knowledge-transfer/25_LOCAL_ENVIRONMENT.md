<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 25: Local Windows Development & Runtime Environment

Finova AI is architected as an offline-first, local-first enterprise intelligence system. Unlike cloud-native SaaS applications that offload computation to managed clusters (AWS ECS, Google Cloud Run, Snowflake, Pinecone), Finova AI executes entirely on the host operating system. The production-grade target deployment environment is modern 64-bit Windows (Windows 11 / Windows Server 2022) with PowerShell 7 / Windows PowerShell 5.1.

This document details the exact local execution environment, process orchestration, inter-process communication, port topology, process lifetimes, and low-level OS quirks—such as character encoding collisions on Windows console outputs—and traces the unified launcher script `scripts/run_local.py`.

---

## 1. Operating System & Toolchain Topology

```
+-----------------------------------------------------------------------------------------+
|                                    WINDOWS 11 HOST                                      |
|                                                                                         |
|  +-------------------------------------+      +--------------------------------------+  |
|  |           POWERSHELL                |      |           GOOGLE CHROME /            |  |
|  |   Terminal Session (UTF-8 / CP1252) |      |         EDGE (Blink Engine)          |  |
|  +------------------+------------------+      +------------------+-------------------+  |
|                     |                                            |                      |
|                     | invokes                                    | opens                |
|                     v                                            v                      |
|      [ .venv-finova\Scripts\python.exe ]            [ http://localhost:5173 ]           |
|            (Python 3.13.15 64-bit)                               |                      |
|                     |                                            |                      |
|                     | executes                                   |                      |
|                     v                                            |                      |
|           [ scripts/run_local.py ]                               |                      |
|             (Parent Orchestrator)                                |                      |
|                     |                                            |                      |
|         +-----------+-----------+                                |                      |
|         | forks                 | forks                          |                      |
|         v                       v                                |                      |
|  +--------------------+  +---------------------+                 |                      |
|  |   Uvicorn Worker   |  |   Vite Dev Server   | <---------------+                      |
|  |  (FastAPI Backend) |  | (React / TypeScript)|                                        |
|  |  Port: 127.0.0.1:  |  |  Port: 127.0.0.1:   |                                        |
|  |        8000        |  |        5173         |                                        |
|  +---------+----------+  +----------+----------+                                        |
|            |                        |                                                   |
|            | RAG / Tools / Safety   | Proxies /api and /health                          |
|            v                        +-------------------------+                         |
|  +---------------------------------------------------------+  |                         |
|  |                      LOCAL SUBSYSTEMS                   |  |                         |
|  |                                                         |  |                         |
|  |  +------------------------+  +-----------------------+  |  |                         |
|  |  |  Ollama Local Daemon   |  |  FastEmbed / Qdrant   |  |  |                         |
|  |  | (qwen2.5:7b-instruct)  |  | (Local File-Backed)   |  |  |                         |
|  |  | Port: 127.0.0.1:11434  |  | data/qdrant_storage/  |  |  |                         |
|  |  +------------------------+  +-----------------------+  |  |                         |
|  |                                                         |  |                         |
|  |  +------------------------+  +-----------------------+  |  |                         |
|  |  | SQLite Conversations   |  |  SQLite Memory DB     |  |  |                         |
|  |  | data/conversations.db  |  |  data/memory.db       |  |  |                         |
|  |  +------------------------+  +-----------------------+  |  |                         |
|  +---------------------------------------------------------+  |                         |
|                                                               |                         |
+---------------------------------------------------------------+-------------------------+
```

### 1.1 Verified Toolchain Versions `[FACT]`
Fresh verification executed against the live host environment on 2026-09-13:
- **Operating System**: Windows 11 Home / Pro 64-bit (`win32` platform).
- **Python**: `3.13.15` 64-bit (`.venv-finova\Scripts\python.exe`).
- **Node.js**: `v24.21.0` (LTS baseline).
- **npm**: `11.19.0`.
- **PowerShell**: Windows PowerShell 5.1 / PowerShell Core 7.x compatible.
- **Ollama**: Local service daemon listening on `127.0.0.1:11434`.

---

## 2. Virtual Environment (`.venv-finova`) Architecture

Finova AI isolates all Python dependencies from the system interpreter via a dedicated virtual environment directory named `.venv-finova`.

### 2.1 Structure and Directory Layout `[FACT]`
```
c:\Users\prana\OneDrive\Desktop\finova-ai\.venv-finova\
├── Lib\
│   └── site-packages\          # Installed wheels (fastapi, pydantic, qdrant-client, fastembed, etc.)
├── Scripts\
│   ├── python.exe              # Target interpreter binary (3.13.15)
│   ├── pythonw.exe             # Windowless interpreter binary
│   ├── pip.exe                 # Package manager
│   ├── uvicorn.exe             # ASGI server executable
│   ├── pytest.exe              # Test runner executable
│   ├── Activate.ps1            # PowerShell activation script
│   └── activate.bat            # Legacy Windows command prompt activation script
└── pyvenv.cfg                  # Python virtual environment configuration
```

### 2.2 Activation vs. Direct Invocation `[FACT]`
Under Windows PowerShell, script execution is frequently constrained by `ExecutionPolicy` (e.g. `Restricted` or `RemoteSigned`). 
While `.venv-finova\Scripts\Activate.ps1` modifies the current shell session's `$env:PATH` and `$env:VIRTUAL_ENV`, Finova's automated scripts avoid execution policy friction by **directly invoking the virtual environment binary**:
```powershell
# Preferred direct invocation:
.venv-finova\Scripts\python.exe scripts/run_local.py

# Instead of relying on shell activation:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\.venv-finova\Scripts\Activate.ps1
# python scripts/run_local.py
```

### 2.3 Static Analysis & IDE Resolver Bindings `[FACT]`
To prevent IDEs (Antigravity IDE, VS Code, PyCharm) from attempting to resolve packages against the global Windows Python path, two explicit configuration files bind the workspace to `.venv-finova`:
1. `pyrightconfig.json` (Commit `d782dac`):
   ```json
   {
     "venvPath": ".",
     "venv": ".venv-finova"
   }
   ```
2. `pyrefly.toml` (Commit `46e51ca`):
   Configures the language server environment to locate `.venv-finova\Scripts\python.exe`.

---

## 3. Port Topology and Network Binding

Finova AI binds strictly to localhost IPv4 addresses to prevent accidental exposure on local area networks (LANs).

| Service | Port | Host Binding | Transport | Protocol | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ollama Daemon** | `11434` | `127.0.0.1` | TCP | HTTP/1.1 REST | Local LLM inference (`qwen2.5:7b-instruct`) |
| **FastAPI Backend** | `8000` | `127.0.0.1` | TCP | HTTP/1.1 ASGI | Application API, safety, RAG, tools |
| **Vite Dev Server** | `5173` | `localhost` | TCP | HTTP/1.1 + WS | React frontend UI, HMR websocket |

### 3.1 `127.0.0.1` vs. `localhost` on Windows `[FACT]`
On Windows systems, resolving the hostname `localhost` can trigger dual-stack name resolution through the Windows `hosts` file (`C:\Windows\System32\drivers\etc\hosts`) or DNS:
1. `::1` (IPv6 loopback)
2. `127.0.0.1` (IPv4 loopback)

If an ASGI server (Uvicorn) binds only to `127.0.0.1`, a client connecting to `http://localhost:8000` may first attempt `::1:8000`, encounter a socket `WSAECONNREFUSED` (10061), and delay 1,000–2,000ms before falling back to `127.0.0.1`.
**Finova Rule**:
- Backend services bind explicitly to `127.0.0.1` (`app.main:app --host 127.0.0.1 --port 8000`).
- Health checks in `scripts/run_local.py` check `http://127.0.0.1:8000/health` and `http://127.0.0.1:11434/api/tags` directly, avoiding DNS loopback resolution latency.
- Vite's dev server proxies `/api` and `/health` to `http://127.0.0.1:8000` in `frontend/vite.config.ts`.

---

## 4. Windows Character Encoding (CP1252 vs. UTF-8)

One of the most insidious bugs on Windows development environments is the legacy console character encoding.

### 4.1 The Problem `[FACT]`
By default, standard Windows PowerShell and CMD sessions run with code page **Windows-1252 (CP1252)** or **OEM 437**.
Finova AI heavily utilizes financial and informational Unicode characters:
- Indian Rupee Currency Symbol: `₹` (`\u20b9`)
- Quotation characters: `“`, `”`, `‘`, `’` (`\u201c`, `\u201d`)
- Math operators: `≥`, `≤`, `≈` (`\u2265`, `\u2264`)
- Emoji status indicators: `🟢`, `🔴`, `⚠️`, `✅`

When a Python script executes `print("₹10,000")` on a standard Windows console with CP1252 encoding, Python's `charmap` codec attempts to map `\u20b9` into the 8-bit CP1252 table. Because `\u20b9` does not exist in CP1252, Python raises a fatal unhandled exception:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9' in position 0: character maps to <undefined>
```
This crash would instantly terminate CLI runners, data ingestion scripts (`scripts/ingest_docs.py`), or backend workers logging financial strings to standard output.

### 4.2 The Solution Implemented in `scripts/run_local.py` `[FACT]`
In `scripts/run_local.py` (lines 46–51):
```python
# Ensure stdout handles UTF-8 cleanly on Windows consoles (e.g. CP1252)
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
```
By calling `sys.stdout.reconfigure(encoding="utf-8")` at the earliest entry point, Python instructs the Windows console stream wrapper to encode all output text as UTF-8, allowing ₹ currency symbols, bullet points, and log markers to print without crashing. Furthermore, setting `$env:PYTHONIOENCODING="utf-8"` in PowerShell sessions guarantees identical protection across interactive subshells.

---

## 5. Configuration & Environment Hierarchy (`.env`)

Finova AI utilizes Pydantic Settings (`pydantic-settings`) in `app/core/config.py` for type-safe environment variable parsing.

### 5.1 Variable Resolution Order `[FACT]`
1. **OS Environment Variables**: Set in the active shell session (e.g. `$env:APP_PORT="8080"`).
2. **Local `.env` File**: Located at the project root (`c:\Users\prana\OneDrive\Desktop\finova-ai\.env`).
3. **Pydantic Model Defaults**: Defined in `app/core/config.py`.

### 5.2 Canonical Configuration Template (`.env.example`) `[FACT]`
```ini
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

### 5.3 Default Key Invariants `[FACT]`
- `APP_ENV`: Defaults to `"development"`. Controls FastAPI docs (`/docs` and `/openapi.json`).
- `APP_HOST`: Defaults to `"127.0.0.1"`.
- `APP_PORT`: Defaults to `8000`.
- `OLLAMA_HOST`: Defaults to `"http://localhost:11434"`.
- `OLLAMA_MODEL`: Defaults to `"qwen2.5:7b-instruct"`.
- Zero required cloud API keys: `TWELVE_DATA_API_KEY` is optional (system falls back to Yahoo Finance and CoinGecko public endpoints).

---

## 6. Execution Trace: `scripts/run_local.py`

When a developer executes:
```powershell
.venv-finova\Scripts\python scripts/run_local.py
```
The script acts as a master process supervisor. Below is the exact step-by-step trace through `scripts/run_local.py` (117 lines of Python).

```
[Developer Command]
       |
       v
1. [Platform Check & Console Reconfiguration]
   sys.platform == "win32" -> sys.stdout.reconfigure(encoding="utf-8")
       |
       v
2. [Step 1: Ollama Probe]
   GET http://127.0.0.1:11434/api/tags (timeout: 2.0s)
   +-- If 200 OK: log("[OK] Ollama is running and responsive.")
   +-- If Error/Timeout: log("[!] Ollama was not detected... Start it with 'ollama serve'")
       |
       v
3. [Step 2: FastAPI Backend Check & Spawn]
   GET http://127.0.0.1:8000/health (timeout: 2.0s)
   +-- If 200 OK: log("[OK] Backend is already running.")
   +-- If Not Running:
         subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", 
                          "--host", "127.0.0.1", "--port", "8000"], cwd=repo_root)
         Poll /health loop: up to 10 iterations x 0.5s = 5.0s max wait
       |
       v
4. [Step 3: Frontend Dependency Check]
   Check if frontend/node_modules/ exists.
   +-- If missing: subprocess.run(["npm", "install"], cwd="frontend/", shell=True, check=True)
       |
       v
5. [Step 4: Vite Server Launch]
   log("Starting Vite development server on http://localhost:5173...")
   subprocess.run(["npm", "run", "dev"], cwd="frontend/", shell=True)
       |
       v
6. [Interactive Session]
   Vite dev server runs in foreground. Backend runs in background child process.
       |
       v
7. [Shutdown Handler (Ctrl+C)]
   KeyboardInterrupt caught -> finally block:
   backend_proc.terminate() -> backend_proc.wait() -> clean exit code 0.
```

### 6.1 Step-by-Step Code Walkthrough `[FACT]`

#### Phase 1: Encoding Sanitization (Lines 46–51)
Checks `sys.platform == "win32"` and reconfigures `sys.stdout` to UTF-8. Emits the startup banner.

#### Phase 2: Probe Ollama (Lines 57–66)
Executes `check_ollama("http://127.0.0.1:11434")`. Makes an HTTP GET request to `/api/tags` with a 2.0s timeout using `urllib.request`. If Ollama is offline, prints a graceful non-blocking warning informing the user that deterministic tools and calculations will still work, while generative RAG answers require Ollama.

#### Phase 3: Probe & Spawn Backend (Lines 67–90)
Executes `check_backend_running("http://127.0.0.1:8000")`. If an instance is already alive (status 200 on `/health`), it reuses it. Otherwise, it spawns Uvicorn using the exact Python executable currently running the script (`sys.executable`):
```python
backend_proc = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)
```
It enters a polling loop (10 retries at 0.5s intervals = 5 seconds max) testing `http://127.0.0.1:8000/health` until Uvicorn completes lifespan initialization (loading SQLite databases, Qdrant vectors, and safety rules).

#### Phase 4: Frontend Node Modules & Vite Server (Lines 91–105)
Inspects `frontend/node_modules`. If the directory does not exist, it runs `npm install` automatically. Next, it executes `npm run dev` in the `frontend` directory. Under Vite, this binds the local frontend server to `http://localhost:5173` and displays:
```
Open your browser at: http://localhost:5173
```

#### Phase 5: Supervised Shutdown (Lines 105–112)
When the user presses `Ctrl+C`, Python raises a `KeyboardInterrupt`. The `finally` block detects if `backend_proc` was launched by this process and sends `backend_proc.terminate()`, awaiting its exit via `backend_proc.wait()` to prevent orphan Uvicorn processes occupying port 8000.

---

## 7. Development vs. Production Execution Profiles

| Feature / Dimension | Local Development (`scripts/run_local.py`) | Production / Isolated Evaluation |
| :--- | :--- | :--- |
| **Backend Execution** | `uvicorn app.main:app --host 127.0.0.1 --port 8000` | Same (or behind Nginx / Windows Service) |
| **Frontend Execution** | Vite Dev Server (`npm run dev`) with HMR | Static bundle (`npm run build` -> `frontend/dist/`) |
| **Asset Delivery** | Node process via websocket HMR on `:5173` | Static files served via FastAPI `StaticFiles` or Nginx |
| **Database Storage** | Local SQLite files in `data/*.db` | Dedicated local SSD mount for SQLite files |
| **Vector Storage** | Embedded Qdrant in `data/qdrant_storage/` | Same local file-backed Qdrant engine |
| **Model Weights** | Ollama local disk store (`~/.ollama/models`) | Pre-pulled `qwen2.5:7b-instruct` model weights |

---

## 8. Verification & Diagnostic Commands `[FACT]`

To verify the integrity of the local environment from PowerShell without starting the entire application stack:

```powershell
# 1. Verify Python & Virtual Environment
.venv-finova\Scripts\python.exe --version
# Expected output: Python 3.13.15

# 2. Verify Node & npm
node --version
npm --version
# Expected output: v24.x, 11.x

# 3. Test Ollama connectivity
curl.exe -s http://127.0.0.1:11434/api/tags
# Expected: JSON containing "models" array with "qwen2.5:7b-instruct"

# 4. Run test suite
.venv-finova\Scripts\pytest.exe -q
# Expected: 525 passed in ~200s
```
