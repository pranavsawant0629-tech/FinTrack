<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 26: Practical Finova Command Handbook

This handbook provides an authoritative, practical reference for every command executed during the development, testing, operation, and release packaging of Finova AI. Every command is grounded in actual project usage, with high-level mechanics, real-world invocations, and common developer pitfalls.

---

## 1. Python Environment & Dependency Commands

### 1.1 `python -m venv`

- **WHAT**: The standard library command to create a lightweight, isolated Python virtual environment.
- **WHY**: Isolates project dependencies from the global system Python installation, preventing package version collisions across different local projects.
- **HOW IT WORKS AT A HIGH LEVEL**: Creates a directory tree containing a copy of or symlink to the Python interpreter, standard library modules, a `site-packages` directory for third-party wheels, and platform-specific activation scripts in `Scripts/` (Windows) or `bin/` (Unix).
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  python -m venv .venv-finova
  ```
  Created the authoritative virtual environment `.venv-finova` at the project root for Python 3.13.15.
- **COMMON MISTAKES**:
  - Running without `.venv-finova` activated, accidentally installing dependencies into the global Windows user environment (`AppData\Local\Programs\Python\...`).
  - Committing the virtual environment directory to Git (Finova prevents this via `.gitignore` entry `/.venv-finova/` and `venv/`).

---

### 1.2 `pip install`

- **WHAT**: The standard Python package installer command.
- **WHY**: Fetches, compiles (if necessary), and installs Python wheels and packages from the Python Package Index (PyPI) or local wheels into the active environment's `site-packages`.
- **HOW IT WORKS AT A HIGH LEVEL**: Resolves package dependencies, downloads wheels or tarballs, verifies hashes and metadata, and writes library files and entry points to `.venv-finova\Lib\site-packages` and `.venv-finova\Scripts`.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  .venv-finova\Scripts\pip.exe install -r requirements.txt
  ```
  Installs all backend runtime and evaluation dependencies: `fastapi`, `uvicorn`, `pydantic`, `qdrant-client`, `fastembed`, `pypdf`, `httpx`, `pytest`, etc.
- **COMMON MISTAKES**:
  - Running bare `pip install <pkg>` without updating `requirements.txt`, leading to deployment drift.
  - Calling `pip` from global CMD instead of referencing `.venv-finova\Scripts\pip.exe`.

---

### 1.3 `pip freeze`

- **WHAT**: Emits the complete list of all currently installed Python packages and their exact pinned versions to standard output.
- **WHY**: Generates reproducible dependency locks (`requirements.txt`) so that any engineer or automated runner installs identical package versions.
- **HOW IT WORKS AT A HIGH LEVEL**: Scans `.venv-finova\Lib\site-packages` for `.dist-info` directories, reads package metadata files, and formats each package as `name==version`.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  .venv-finova\Scripts\pip.exe freeze > requirements.lock
  ```
  Used to audit package dependencies and freeze release baselines.
- **COMMON MISTAKES**:
  - Redirecting `pip freeze` directly into `requirements.txt` without pruning transient, platform-specific, or editable packages.

---

## 2. Testing & Quality Assurance Commands

### 2.1 `pytest`

- **WHAT**: The premier Python test framework and test runner.
- **WHY**: Automatically discovers, executes, asserts, and reports unit, integration, safety, and evaluation test suites across the codebase.
- **HOW IT WORKS AT A HIGH LEVEL**: Recursively discovers test files matching `test_*.py` or `*_test.py`, instantiates test functions and classes, manages fixtures, injects dependencies, runs assertions, captures stdout/stderr, and reports timing and pass/fail statuses.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  # Full test suite run across all 50 test files:
  .venv-finova\Scripts\pytest.exe

  # Quick summary run:
  .venv-finova\Scripts\pytest.exe -q

  # Run specific domain test file:
  .venv-finova\Scripts\pytest.exe tests/test_red_team_safety.py -v

  # Run with timing profiler:
  .venv-finova\Scripts\pytest.exe --durations=10
  ```
  Verified result: **525 passed, 4 warnings in ~207.0s**.
- **COMMON MISTAKES**:
  - Running with the wrong working directory, causing relative fixture paths (`tests/fixtures/...` or `data/...`) to fail.
  - Running without Qdrant or embedding model pre-cached, causing network timeouts in offline CI environments.

---

## 3. Version Control (Git) Commands

### 3.1 `git status`

- **WHAT**: Inspects the working directory and staging area (index) against the current `HEAD` commit.
- **WHY**: Displays tracked modified files, staged changes ready for commit, untracked files, and current branch tracking state.
- **HOW IT WORKS AT A HIGH LEVEL**: Compares file hashes and modification timestamps (stat cache) of the working tree against the Git index and `HEAD` commit tree.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git status
  git status --short
  ```
  Used repeatedly across every phase gate to guarantee zero untracked side-effects or unexpected repository modifications.
- **COMMON MISTAKES**:
  - Assuming untracked files will be saved in a commit without staging them first with `git add`.

---

### 3.2 `git log`

- **WHAT**: Displays the chronological commit history of the repository.
- **WHY**: Enables inspection of development progression, author attribution, commit messages, and specific tree hashes.
- **HOW IT WORKS AT A HIGH LEVEL**: Traverses the directed acyclic graph (DAG) of commit objects backwards from `HEAD` following parent pointers.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  # Inspect recent commits:
  git log --oneline -5

  # Full chronological trace in reverse:
  git log --pretty=format:"%h | %as | %s" --reverse

  # Inspect specific file modifications:
  git log -p -2 app/safety/validator.py
  ```
- **COMMON MISTAKES**:
  - Getting trapped in the default Windows terminal pager (`less` or `more`) without knowing that pressing `q` exits the pager.

---

### 3.3 `git diff`

- **WHAT**: Computes and displays line-by-line differences between Git trees, the index, and the working tree.
- **WHY**: Enables granular visual review of source code changes before staging or committing.
- **HOW IT WORKS AT A HIGH LEVEL**: Uses Myers difference algorithm to compare blobs, generating unified diff chunks with line numbers and added/removed tokens.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  # Check unstaged working tree changes:
  git diff

  # Check staged changes ready to be committed:
  git diff --staged

  # Inspect diff between Phase 13 and public packaging:
  git diff d64eb5f..42228bb README.md
  ```
- **COMMON MISTAKES**:
  - Running `git diff` and seeing no output because all changes have already been staged (requires `git diff --staged` or `git diff --cached`).

---

### 3.4 `git add`

- **WHAT**: Stages file modifications from the working directory into the Git index.
- **WHY**: Prepares a curated snapshot of changes to be committed together in an atomic commit.
- **HOW IT WORKS AT A HIGH LEVEL**: Reads file content, compresses it into SHA-1/SHA-256 content-addressable blob objects in `.git/objects`, and updates the `.git/index` binary file with hashes and path entries.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git add app/safety/validator.py tests/test_red_team_safety.py
  ```
- **COMMON MISTAKES**:
  - Running `git add .` recklessly, accidentally staging sensitive temporary files, `.env` credentials, or database files (`data/conversations.db`).

---

### 3.5 `git commit`

- **WHAT**: Records staged snapshot changes permanently into the Git repository history.
- **WHY**: Creates an immutable point in time with an explanatory message, author metadata, and parent commit links.
- **HOW IT WORKS AT A HIGH LEVEL**: Writes a `tree` object representing the directory structure, writes a `commit` object referencing the tree and parent commit SHA, and updates the active branch reference (`refs/heads/main`) to point to the new commit.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git commit -m "feat(phase13): complete end-to-end QA and release readiness"
  ```
- **COMMON MISTAKES**:
  - Writing vague, non-standard commit messages that obscure what subsystem was altered. Finova strictly follows conventional commit syntax (`feat(...)`, `fix(...)`, `chore(...)`, `docs(...)`).

---

### 3.6 `git branch`

- **WHAT**: Lists, creates, or deletes branch references.
- **WHY**: Manages parallel lines of development and tracks upstream remote branches.
- **HOW IT WORKS AT A HIGH LEVEL**: Manipulates plain-text pointer files located in `.git/refs/heads/` and `.git/refs/remotes/`.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git branch -a -v
  ```
  Verified active local branch `main` and remote tracking branch `remotes/origin/main`.
- **COMMON MISTAKES**:
  - Developing on a detached `HEAD` state without a named branch pointer, risking lost commits during garbage collection.

---

### 3.7 `git remote`

- **WHAT**: Manages tracked remote repositories (connections to GitHub, GitLab, etc.).
- **WHY**: Allows syncing local commits with remote collaborative or distribution servers.
- **HOW IT WORKS AT A HIGH LEVEL**: Reads and updates the `[remote "name"]` section in `.git/config`, mapping remote URLs to remote ref namespaces (`refs/remotes/origin/*`).
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git remote -v
  ```
  Output verified:
  `origin  https://github.com/pranavsawant0629-tech/finova-ai.git (fetch)`
  `origin  https://github.com/pranavsawant0629-tech/finova-ai.git (push)`
- **COMMON MISTAKES**:
  - Configuring HTTP remotes with plaintext credentials in the URL instead of using Git Credential Manager or SSH keys.

---

### 3.8 `git push`

- **WHAT**: Transmits local commit objects, trees, blobs, and branch references to a remote Git server.
- **WHY**: Publishes local work to GitHub so it can be cloned, reviewed, or deployed.
- **HOW IT WORKS AT A HIGH LEVEL**: Negotiates common ancestry with the remote via Git pack protocol, bundles missing objects into a compressed packfile, uploads it, and updates the remote branch ref if fast-forwardable.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  git push -u origin main
  ```
  Executed during the authorized release gate to publish Phase 13 / public packaging to GitHub.
- **COMMON MISTAKES**:
  - Force-pushing (`git push --force`) onto shared branches, obliterating upstream commits.

---

## 4. Frontend & Node.js Commands

### 4.1 `npm install`

- **WHAT**: Installs JavaScript and TypeScript dependencies defined in `frontend/package.json`.
- **WHY**: Fetches and populates the `frontend/node_modules` directory with libraries needed to build and run the React frontend (`react`, `react-dom`, `lucide-react`, `vite`, `typescript`, etc.).
- **HOW IT WORKS AT A HIGH LEVEL**: Reads `package.json` and `package-lock.json`, downloads tarballs from the npm registry, validates SHA integrity checksums, and resolves the nested dependency graph into `node_modules`.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  cd frontend
  npm install
  ```
  Automated in `scripts/run_local.py` if `frontend/node_modules` is detected missing.
- **COMMON MISTAKES**:
  - Running `npm install` in the project root directory instead of `frontend/`, creating an unintended root `node_modules` directory.

---

### 4.2 `npm run dev`

- **WHAT**: Launches Vite's local development server.
- **WHY**: Provides instant hot module replacement (HMR), local asset compilation, and development proxying.
- **HOW IT WORKS AT A HIGH LEVEL**: Starts a Node.js server using ES module imports directly in the browser (no bundle step required during dev), establishing a WebSocket on port 5173 for instantaneous module reloading when `.tsx` or `.css` files change.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  cd frontend
  npm run dev
  ```
  Runs Vite on `http://localhost:5173`, proxying `/api` requests to Uvicorn at `http://127.0.0.1:8000`.
- **COMMON MISTAKES**:
  - Forgetting that Vite binds to `localhost:5173` while Uvicorn binds to `127.0.0.1:8000`. If proxy config is misaligned, API requests fail with 404 or connection refused.

---

### 4.3 `npm run build`

- **WHAT**: Compiles and bundles TypeScript and React code into optimized production assets.
- **WHY**: Validates that all TypeScript types are sound, strips comments/whitespace, tree-shakes dead code, and generates minified HTML, CSS, and JS chunks in `frontend/dist/`.
- **HOW IT WORKS AT A HIGH LEVEL**: First invokes the TypeScript compiler `tsc -b` to enforce static type checking without emitting files, then invokes Vite to bundle assets via Rollup.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  cd frontend
  npm run build
  ```
  Used in release audits to prove zero TypeScript compilation errors across all frontend components.
- **COMMON MISTAKES**:
  - Bypassing `npm run build` before pushing to release, allowing undetected TypeScript syntax or typing errors to slip into the repository.

---

### 4.4 `npm run lint`

- **WHAT**: Runs ESLint across frontend source files.
- **WHY**: Enforces code style, catches common React hooks mistakes (`react-hooks/exhaustive-deps`), and flags unused variables.
- **HOW IT WORKS AT A HIGH LEVEL**: Parses TypeScript files into an Abstract Syntax Tree (AST), runs AST linting rules, and reports line-by-line warnings and errors.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  cd frontend
  npm run lint
  ```
- **COMMON MISTAKES**:
  - Suppressing lint rules with `eslint-disable` instead of addressing root hook dependency issues.

---

## 5. Server & Daemon Commands

### 5.1 `uvicorn`

- **WHAT**: A lightning-fast ASGI (Asynchronous Server Gateway Interface) web server implementation for Python.
- **WHY**: Serves FastAPI applications, managing HTTP request/response lifecycles, WebSocket connections, concurrency, and application lifespan startup/shutdown events.
- **HOW IT WORKS AT A HIGH LEVEL**: Utilizes `asyncio` event loops (or `uvloop` on Unix) to parse HTTP requests via `httptools`, dispatching ASGI events to FastAPI route handlers.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  .venv-finova\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
  Configured in `scripts/run_local.py` to start the backend supervisor.
- **COMMON MISTAKES**:
  - Specifying `--reload` in production scripts, which spawns dual processes and creates file-watching overhead on Windows disk I/O.

---

### 5.2 `ollama`

- **WHAT**: The local large language model runner and model management daemon.
- **WHY**: Runs quantized GGUF neural network models locally on consumer CPU/GPU hardware without cloud API dependencies.
- **HOW IT WORKS AT A HIGH LEVEL**: Built on `llama.cpp`. Manages model quantization (Q4_K_M), loads tensor layers into available GPU VRAM (NVIDIA CUDA / AMD ROCm) or CPU RAM, and exposes an HTTP REST API on `127.0.0.1:11434`.
- **FINOVA USAGE `[FACT]`**:
  ```powershell
  # Start Ollama background service:
  ollama serve

  # Pull required Finova model:
  ollama pull qwen2.5:7b-instruct

  # List locally installed models:
  ollama list

  # Verify API responsiveness:
  curl.exe -s http://127.0.0.1:11434/api/tags
  ```
- **COMMON MISTAKES**:
  - Attempting to run RAG generation without starting `ollama serve` first.
  - Pulling an uninstructed base model (`qwen2.5:7b`) instead of the required instruction-tuned model (`qwen2.5:7b-instruct`), causing chaotic text completions instead of structured answers.
