# Finova AI — Local Product Trial Guide

This guide describes how to run and evaluate **Finova AI** locally as a standalone, production-grade financial education assistant.

---

## 1. Architecture Overview

Finova AI operates as a unified, multi-agent financial intelligence assistant:

- **Frontend (`frontend/`)**: Vite + React 19 + TypeScript + Tailwind CSS v4, running on `http://localhost:5173`.
- **Backend (`app/`)**: FastAPI multi-agent orchestrator with CORS enabled, running on `http://127.0.0.1:8000`.
- **Inference Runtime (`Ollama`)**: Local LLM (`qwen2.5:7b-instruct`) and embedding model (`bge-m3:latest`) on `http://127.0.0.1:11434`.

---

## 2. Prerequisites

1. **Python 3.10+**: with dependencies installed in the virtual environment (`.venv-finova`).
2. **Node.js 18+ and npm**: for the frontend application.
3. **Ollama (Optional for deterministic math, Recommended for full RAG)**:
   ```bash
   ollama run qwen2.5:7b-instruct
   ollama pull bge-m3:latest
   ```

---

## 3. Quick Start (Single-Command)

Run the unified local runner script from the project root:

```bash
.venv-finova\Scripts\python scripts/run_local.py
```

This will:
1. Verify that Ollama is responding on `http://127.0.0.1:11434`.
2. Check or launch the FastAPI backend on `http://127.0.0.1:8000`.
3. Launch the Vite frontend dev server and prompt you to open `http://localhost:5173`.

---

## 4. Manual Startup (Separate Terminals)

If you prefer running services in separate terminal windows:

### Terminal 1 — Backend
```powershell
.venv-finova\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2 — Frontend
```powershell
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 5. Trial Exploration Checklist

Use the following queries and interactions during the 2–3 day trial to evaluate all 8 specialized domains and orchestration capabilities:

### A. Live Indian Equity Quotes
- **Query:** `"What is the live price of TCS and what is its market status?"`
- **Expected UI:** Rich `MarketQuoteCard` showing price in `₹`, change, market session, timestamp freshness, and NSE/BSE provenance.

### B. Compounding & Personal Finance
- **Query:** `"If I invest ₹5,000 monthly in an equity mutual fund at 12% for 10 years, what is the future value and wealth gain?"`
- **Expected UI:** Deterministic compounding breakdown, wealth gained, total invested, and educational explanation of time horizon.

### C. Options & Derivatives Payoff
- **Query:** `"Explain how a Bull Call Spread works with buy strike 22000 at premium 120 and sell strike 22200 at premium 40."`
- **Expected UI:** Interactive `PayoffTableCard` with underlying prices, net profit/loss, max profit, max loss, and calculated breakeven price.

### D. Simulated Portfolio & What-If Stress Testing
- **Query:** `"Simulate a 10% drop in NIFTY on my simulated portfolio and show the projected impact."`
- **Expected UI:** `PortfolioCard` displaying original value, simulated value, projected percentage and rupee impact, and holding-by-holding stress results.

### E. Cryptocurrency Analytics
- **Query:** `"What is the price of Bitcoin in INR and its 24h market change?"`
- **Expected UI:** `CryptoCard` displaying dual-currency (INR/USD) values, 24h change %, and CoinGecko attribution.

### F. Market News & Regulatory Updates
- **Query:** `"What are the latest regulatory updates and news regarding Indian markets?"`
- **Expected UI:** `NewsCard` displaying structured news articles with verified source badges and publishing timestamps.

### G. Interactive Financial Education Quiz
- **Query:** `"Give me an educational quiz on mutual funds and risk management."`
- **Expected UI:** Interactive `QuizCard` with selectable options. Click an option and click "Submit Answers" to see immediate grading and explanations.

### H. Multi-Intent Compound Query
- **Query:** `"What is the price of Infosys and how does an emergency fund work?"`
- **Expected UI:** Multi-intent decomposition showing `SubtasksSummary` domain chips (`EQUITY` + `PERSONAL_FINANCE`), followed by both answers and market quote cards.

### I. Persistent Learner Identity & Clear Memory
1. Click your profile badge in the top right header to open the **Learner Identity & Memory** modal.
2. Note your persistent `user_id` stored in browser `localStorage`.
3. Update your preferred **Display Name** and save.
4. View persistent educational memories recorded by the backend.
5. Click **"Clear Memory"** to test compliance and verify memory reset.

---

## 6. Gaps & Trial Observations

1. **Portfolio Default ID:** The backend defaults portfolio operations to `"demo_user"` when no custom holdings exist. The frontend passes the user's persistent `user_id` wherever accepted, but the demo portfolio serves as a standardized baseline.
2. **Elapsed-Time Feedback:** Since the backend orchestrator responds as a complete JSON payload after full synthesis (~2–15 seconds depending on local Ollama hardware), an honest elapsed-time counter is shown rather than simulated progress phases.
3. **Regulatory Safety Invariant:** Finova AI provides educational analysis and simulations only. It does not provide individualized investment advice or order execution.
