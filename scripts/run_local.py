"""
Finova AI — Local Development & Trial Launcher.
Checks local prerequisites (Ollama, Python virtualenv, FastAPI, Node/Vite)
and provides a single unified entrypoint for local evaluation.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


def log(prefix: str, msg: str) -> None:
    print(f"[{prefix}] {msg}")


def check_ollama(url: str = "http://127.0.0.1:11434") -> bool:
    """Checks if the local Ollama server is running and accessible."""
    try:
        req = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    return False


def check_backend_running(url: str = "http://127.0.0.1:8000") -> bool:
    """Checks if the FastAPI backend is already running."""
    try:
        req = urllib.request.Request(f"{url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass
    return False


def main() -> int:
    # Ensure stdout handles UTF-8 cleanly on Windows consoles (e.g. CP1252)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("FINOVA AI — STANDALONE LOCAL RUNNER")
    print("=" * 60)

    # Step 1: Check Ollama
    log("OLLAMA", "Checking local Ollama service on port 11434...")
    if check_ollama():
        log("OLLAMA", "[OK] Ollama is running and responsive.")
    else:
        log("OLLAMA", "[!] Ollama was not detected on http://127.0.0.1:11434.")
        log("OLLAMA", "  Note: Deterministic tools, quotes, and calculations will work,")
        log("OLLAMA", "  but generative RAG answers require Ollama to be running.")
        log("OLLAMA", "  Start it in another terminal with: 'ollama serve'")

    # Step 2: Check Backend
    log("BACKEND", "Checking FastAPI backend on port 8000...")
    backend_proc = None
    if check_backend_running():
        log("BACKEND", "[OK] Backend is already running on http://127.0.0.1:8000.")
    else:
        log("BACKEND", "Starting local FastAPI server...")
        python_exe = sys.executable
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )
        # Wait up to 5s for startup
        started = False
        for _ in range(10):
            time.sleep(0.5)
            if check_backend_running():
                started = True
                break
        if started:
            log("BACKEND", "[OK] FastAPI backend started on http://127.0.0.1:8000.")
        else:
            log("BACKEND", "[!] Backend launched, waiting for it to accept connections...")

    # Step 3: Frontend Check
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        log("FRONTEND", "Installing frontend dependencies (npm install)...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, shell=True, check=True)

    log("FRONTEND", "Starting Vite development server on http://localhost:5173...")
    log("APP", "Open your browser at: http://localhost:5173")
    print("=" * 60)
    print("Press Ctrl+C to terminate both backend and frontend servers.")
    print("=" * 60)

    try:
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, shell=True)
    except KeyboardInterrupt:
        log("RUNNER", "Shutting down...")
    finally:
        if backend_proc is not None:
            log("BACKEND", "Stopping backend subprocess...")
            backend_proc.terminate()
            backend_proc.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
