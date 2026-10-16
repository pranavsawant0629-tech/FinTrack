# FINOVA AI — PHASE 0 PROGRESS REPORT / HANDOFF

**Status:** Phase 0 (Skeleton / Environment) — COMPLETE
**Date:** As of current session
**Prepared for:** Handoff to Google Antigravity for continued phase-by-phase development

---

## 1. Project Summary

Finova AI is an India-first AI financial education and paper-trading assistant, being built as a separate, independent backend for an existing frontend project called **TradeWise**. TradeWise must NOT be modified or integrated with until the Finova backend is stable (Phase 9). Full architecture, roadmap, and rules are documented in:

- `project-info/Finova_AI_Final_Project_Plan.md`
- `project-info/deep-research-report.md`

These two documents remain the authoritative specification. Nothing in this report overrides them — this report only records what has been verified and implemented so far.

---

## 2. Development Workflow Rules (must be preserved)

- Strictly **phase-by-phase**. Do not implement multiple phases at once.
- Before implementing a phase: inspect current state, propose a plan, list files to create/modify, explain key decisions, **then stop and wait for explicit approval**.
- After implementing a phase: report what was built, what was tested, results, what remains, and **stop and wait for approval** before the next phase.
- Do not fabricate financial numbers or sources.
- Do not add dependencies without a concrete justification — verify what's actually installed before assuming.
- Preserve working functionality; don't rewrite components without reason.
- Git: local commits are fine; **never push to GitHub, never create PRs, never touch TradeWise remotely** without explicit approval.
- Goal: ~₹0 development cost — local/open-source first, minimal dependencies, no paid APIs unless unavoidable.

---

## 3. Verified Environment

- **OS:** Windows
- **Python:** 3.13.15
- **Virtual environment:** `.venv-finova` (already created — do not create another, do not downgrade Python)
- **Ollama:** version 0.34.0, running as a local service
- **LLM model:** `qwen2.5:7b-instruct` (already pulled, verified working on GPU)
- **GPU:** NVIDIA RTX 4050 Laptop GPU, 6GB VRAM — GPU acceleration confirmed working
- Do not replace the current model or jump to a larger model unless benchmarking later demonstrates it's practical on this hardware.

---

## 4. Actual Installed Dependencies (verified via `pip list`, not assumed)

At the start of Phase 0, the venv actually contained only:
```
fastapi, uvicorn, pydantic, python-dotenv, PyYAML, starlette, anyio,
click, h11, httptools, watchfiles, websockets
```

**Important correction:** the `ollama` Python client package was NOT actually pre-installed, despite earlier planning notes assuming it was. This was caught via `pip list` instead of being assumed, then installed properly.

**Current `requirements.txt` (final state after Phase 0):**
```
fastapi
uvicorn
pydantic
python-dotenv
ollama
pytest
httpx
```

Installed versions of note: `fastapi 0.141.1`, `uvicorn 0.52.4`, `pydantic 2.13.5`, `python-dotenv 1.2.3`, `ollama 0.6.2` (pulled in `httpx`, `httpcore`, `certifi` as sub-dependencies), `pytest 9.1.1`.

**Deliberately NOT installed:** `pydantic-settings` (plain `pydantic.BaseModel` + `python-dotenv` was sufficient and avoids an unnecessary dependency).

---

## 5. Project Structure — Current State

```
finova-ai/
├── .venv-finova/              (existing, untouched)
├── app/
│   ├── agents/                 (empty — not started)
│   ├── api/                    (empty — not started)
│   ├── llm/
│   │   ├── __init__.py         (empty, package marker)
│   │   └── llm_client.py       ✅ built + tested
│   ├── memory/                 (empty — not started)
│   ├── rag/                    (empty — not started)
│   ├── router/                 (empty — not started)
│   ├── safety/                 (empty — not started)
│   ├── tools/                  (empty — not started)
│   ├── __init__.py
│   └── main.py                 ✅ built + tested
├── config/
│   ├── __init__.py              (empty, package marker)
│   └── settings.py              ✅ built + tested
├── data/                        (empty — not started)
├── project-info/
│   ├── deep-research-report.md
│   └── Finova_AI_Final_Project_Plan.md
├── scripts/                     (empty — not started)
├── tests/
│   ├── __init__.py               (empty, package marker)
│   └── test_health.py            ✅ built + passing
├── .env                          ✅ configured
├── .gitignore
├── README.md
└── requirements.txt              ✅ updated
```

**Note:** `app/db/` and `app/core/` from the target architecture do not exist yet — intentionally deferred. `app/db/` is expected to be needed starting Phase 5 (SQLite memory/user profile). `app/core/` has no concrete need yet.

---

## 6. Files Implemented in Phase 0 (full contents)

### `.env`
```
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

### `config/settings.py`
```python
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Resolve project root and load .env from there
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")


settings = Settings()
```

### `app/llm/llm_client.py`
```python
import ollama

from config.settings import settings


class LLMClient:
    """
    Abstraction layer over the LLM provider.
    Rest of the app should only talk to this class, never to `ollama` directly.
    """

    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host
        self._client = ollama.Client(host=self.host)

    def chat(self, message: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        response = self._client.chat(model=self.model, messages=messages)
        return response["message"]["content"]


llm_client = LLMClient()
```

### `app/main.py`
```python
from fastapi import FastAPI
from pydantic import BaseModel

from config.settings import settings
from app.llm.llm_client import llm_client

app = FastAPI(title="Finova AI", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "ollama_model": settings.ollama_model,
    }


class TestLLMRequest(BaseModel):
    message: str


@app.post("/test-llm")
def test_llm(payload: TestLLMRequest):
    reply = llm_client.chat(payload.message)
    return {"reply": reply}
```

### `tests/test_health.py`
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ollama_model" in data
```

---

## 7. What Was Tested — Results

| Test | Result |
|---|---|
| `python -c "from config.settings import settings; print(settings)"` | ✅ Correct settings printed |
| `uvicorn app.main:app --reload` boots | ✅ Server starts cleanly on `127.0.0.1:8000` |
| `GET /health` | ✅ Returns `{"status":"ok","env":"development","ollama_model":"qwen2.5:7b-instruct"}` |
| `ollama list` | ✅ Shows `qwen2.5:7b-instruct` installed |
| `llm_client.chat(...)` standalone call | ✅ Returned a real response from the model (after installing missing `ollama` package) |
| `POST /test-llm` via manual HTTP call | ✅ Returned `200` with `{'reply': '...'}` |
| `pytest -v` | ✅ `1 passed` (`tests/test_health.py::test_health_returns_ok`) |

Minor non-blocking note: pytest run showed two `DeprecationWarning`s from Starlette/httpx internals (unrelated to our code, safe to ignore for now).

---

## 8. What Remains (per the approved roadmap)

Phase 0 is complete. Remaining phases, in order, **not yet started**:

- **Phase 1 — RAG Core:** ingest 5–10 real SEBI/NISM documents, chunking + metadata, embeddings (benchmark `BAAI/bge-small-en-v1.5` vs `intfloat/e5-small-v2`), store in **Qdrant** (from the start — no Chroma-then-migrate), implement retrieval, verify relevance manually and automatically.
- **Phase 2 — Equity Agent:** first fully complete agent (persona + RAG-grounded chat + safety), used as the reusable template for all other agents. Do not build all 8 agents at once.
- **Phase 3 — Equity Tools:** deterministic market-data lookup + calculation tools; numbers must always come from tools, never invented by the LLM.
- **Phase 4 — Router + Crypto + Personal Finance agents:** hand-written Python router first (no LangGraph unless workflow complexity genuinely requires it); replicate the Equity agent architecture.
- **Phase 5 — Memory:** conversation context + SQLite user profile + personalization. `app/db/` likely gets created here.
- **Phase 6 — Remaining agents:** Derivatives, Portfolio Advisor, Market News/Trends, Quiz/Challenge, Onboarding/Help.
- **Phase 7 — Hardening:** safety, evaluation, regression tests, performance, logging, failure handling, data freshness/source validation.
- **Phase 8 — Optional standalone UI/deployment** (only if needed).
- **Phase 9 — TradeWise integration:** only after backend stability; define a clean API contract, connect TradeWise. Do not modify TradeWise before this.

---

## 9. Known Open Items / Things to Flag

- `app/db/` and `app/core/` are in the target architecture but not yet created — expected around Phase 5.
- No documents have been collected yet for RAG — Phase 1 will need 5–10 real SEBI/NISM sources selected before ingestion work starts.
- Embedding model choice (`bge-small-en-v1.5` vs `e5-small-v2`) is unresolved — needs benchmarking in Phase 1.
- Qdrant is not yet installed/running locally — will need Docker or local binary setup as part of Phase 1.
- No git commits have been made as part of this session (local commits are allowed per project rules, but none were explicitly requested yet).

---

## 10. Core Principles to Carry Forward

- We are **not** training an LLM from scratch — engineering a system around the LLM: LLM + authoritative RAG + multi-agent routing + deterministic tools + live data + memory + evaluation + safety.
- RAG knowledge must come from authoritative sources only (SEBI, RBI/DBIE, NSE, BSE, AMFI, MCX, NISM/NCFE first; SEC/FINRA/FCA/BIS/IMF/World Bank second tier). Current TradeWise/Finova website content is explicitly **not** authoritative.
- Live market/news data must always come from deterministic tools/providers, never invented by the LLM, with source/timestamp/freshness preserved on every result.
- Educational-only framing throughout — no guaranteed returns, no personalized buy/sell advice presented as professional advice.
- Keep everything modular, testable, and replaceable (LLM provider, embedding model, data providers all swappable via abstraction layers).
