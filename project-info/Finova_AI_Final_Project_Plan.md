# FINOVA AI — FINAL PROJECT PLAN

India-first • Authoritative-source RAG • Local/open-source first • ₹0 development target

## 1. Goal

Build Finova as an industry-style AI financial education system integrated with TradeWise only after the AI backend is proven independently. It teaches finance, retrieves authoritative knowledge, uses current/delayed market and news data, analyzes simulated portfolios, personalizes learning, generates quizzes, and enforces strong financial-safety rules. India is the primary market; international coverage is added through replaceable adapters.

## 2. Core Architecture

TradeWise React → Finova FastAPI → Router/Orchestrator → Specialized Agents → RAG + Memory + Tools → Safety/Evaluation → Structured response.

- Eight agents: Equity, Crypto, Personal Finance, Derivatives, Market News, Portfolio, Quiz/Challenge, Onboarding.

- Router chooses one or more agents; cross-topic questions may combine agents.

- LLM is the reasoning/generation layer, never the source of truth for live prices, calculations, or current regulations.

- Finova is a separate backend/repository, so frontend changes do not block AI development.

## 3. Recommended Tech Stack

- Python 3.11 + FastAPI + Pydantic + Uvicorn.

- Ollama with an abstraction layer; benchmark Qwen2.5-14B-Instruct vs Llama-3.1-8B-Instruct (or current equivalents) against laptop hardware. Do not train an LLM from scratch.

- Keep all model calls behind one llm_client abstraction so the model/provider can later be swapped without rewriting business logic.

- Open-source sentence-transformers embeddings; start with BAAI/bge-small-en-v1.5 or intfloat/e5-small-v2 and benchmark retrieval quality.

- Qdrant from the beginning, self-hosted/local with Docker; avoids a later Chroma→Qdrant migration.

- SQLite for development; PostgreSQL when deployment/multi-user needs justify it.

- Hand-written Python router first; introduce LangGraph only if stateful/cross-agent workflows genuinely become complex.

- Docker Compose for reproducible services once the core system is working.

- pytest + versioned benchmark dataset for testing/evaluation.

## 4. Authoritative Knowledge Strategy

Finova/TradeWise lessons are NOT authoritative. The RAG knowledge base is independently built from trusted sources; Finova/TradeWise content may later be supplementary.

- Tier 1 — Indian regulators/government: SEBI/SEBI Investor, RBI/DBIE, Income Tax Department, Ministry of Finance and other official publications.

- Tier 1 — Indian market institutions: NSE, BSE, AMFI and MCX.

- Tier 2 — Indian financial education: NISM and NCFE.

- Tier 3 — Global authorities where needed: SEC, FINRA, FCA, BIS, IMF, World Bank and comparable institutions.

- Tier 4 — vetted universities/open educational resources and properly licensed textbooks.

- Avoid random finance PDFs, unverified blogs and unclear-license sources.

- Metadata: source, authority level, country, topic, asset/product, publication/update date, URL and licensing/usage status.

## 5. RAG Pipeline

- Collect permitted/trusted documents → parse/clean → chunk → metadata → embeddings → Qdrant.

- Retrieve relevant chunks → authority/topic/date filtering → optional reranking → evidence to agent.

- Generate answers grounded in evidence and expose source/citation information where appropriate.

- Track publication/update dates to identify stale regulatory material.

- Keep stable educational knowledge separate from rapidly changing market/news data.

## 6. India-first Data Layer

- NSE/BSE: Indian equities and indices; prioritize official/permitted data.

- RBI/DBIE: macroeconomic and financial-system data.

- AMFI: mutual-fund information.

- RBI/NSE/BSE: bonds and government securities.

- NSE/BSE/SEBI: derivatives information.

- MCX: Indian commodities.

- Income Tax Department: investment/tax information.

- International markets are added through provider adapters without changing agent architecture.

## 7. Live Market Data & News

- Dedicated tools handle current prices, historical data, company information and market statistics; the LLM never invents current numbers.

- Potential free/accessible providers include Alpha Vantage and Yahoo/yfinance where current terms and limits permit use; official Indian sources remain the priority.

- News: exchange/regulatory announcements, official company announcements and permitted reputable financial-news/RSS sources.

- Store source, timestamp and freshness/status for every live result.

- Explicitly distinguish real-time, delayed and historical data; never claim real-time when data is delayed.

- Use caching and rate limits to remain within free quotas.

- Provider adapters make vendors replaceable.

## 8. Agent Capabilities

- Equity: stocks, ETFs, diversification, fundamentals, chart/technical concepts, company context.

- Crypto: blockchain, major assets, wallets, tokenomics, risks, current information.

- Personal Finance: budgeting, saving, credit, debt, financial planning.

- Derivatives: futures, options, payoff charts, Greeks, hedging, risk.

- Market News: current headlines, movers, source/time, context.

- Portfolio: simulated holdings, allocation, returns, concentration, diversification, basic risk analytics.

- Quiz: adaptive questions, grading, explanations, XP/streak integration, weak-topic detection.

- Onboarding: navigation, feature help, FAQs.

## 9. Tools & Deterministic Logic

- Market tools: prices, historical data, company information, permitted statistics.

- News tools: current news and official announcements.

- Calculation tools: returns, allocation, volatility/basic risk metrics and derivatives payoffs.

- Portfolio tools: simulated holdings and calculations.

- Important numerical outputs come from deterministic code/tool calls, not free-form LLM generation.

## 10. Memory & Personalization

- Short-term memory: current conversation.

- Long-term memory: learning level, completed modules, quiz mistakes, preferences, interests and simulated portfolio context.

- Adapt explanations, examples, quiz difficulty and learning recommendations.

- Minimize retained personal information and provide appropriate privacy/deletion controls.

## 11. Safety & Guardrails

- Educational-first framing; no guaranteed returns.

- Do not present personalized buy/sell decisions as professional investment advice.

- Detect prompt injection, unsafe/illegal requests, unsupported claims and stale data.

- Use authoritative sources for regulatory/factual claims.

- Validate tool outputs and model responses; apply rate limits, audit logs and privacy controls.

## 12. Evaluation

- Benchmark Indian finance, global basics, calculations, RAG, routing, live-data questions and adversarial/safety cases.

- Measure routing accuracy, retrieval relevance, answer correctness, citation correctness, hallucination rate, tool accuracy, latency and safety.

- Run regression tests after changes to models, prompts, retrieval, tools or agents.

- Do not expand to more agents until the current pattern passes its tests.

## 13. Development Roadmap

- Phase 0 — Skeleton: FastAPI, /health, project structure, Ollama model, configuration and tests.

- Phase 1 — RAG Core: ingest 5–10 real SEBI/NISM documents, embeddings + Qdrant, retrieval and manual relevance verification.

- Phase 2 — Complete Equity Agent: persona + RAG chat + safety; prove correctness on a test set.

- Phase 3 — Equity Tools: market-data lookup + deterministic calculations; verify current numbers come from tools.

- Phase 4 — Router + Crypto + Personal Finance: replicate proven architecture and test routing.

- Phase 5 — Memory: conversation context + SQLite profile + personalization.

- Phase 6 — Remaining agents: Derivatives, Portfolio, Market News, Quiz/Challenge, Onboarding.

- Phase 7 — Hardening: safety, evaluation, regression, performance, logging and failure handling.

- Phase 8 — Optional standalone Finova UI/deployment.

- Phase 9 — TradeWise integration: API contract and frontend connection only after backend stability.

## 14. AI-assisted Development

- Use Google Antigravity as the primary coding agent for scoped multi-file implementation/testing.

- Use Claude/Claude Code for difficult architecture, RAG, reasoning and review when available; Cursor is optional for hands-on debugging.

- Never ask an AI agent to build all of Finova in one task.

- Workflow: AI proposes plan/files → human approves → AI implements → tests → human reviews → phase accepted.

- Project constitution: no invented financial numbers; RAG answers cite sources; educational-only framing; tests required; no remote push without approval.

## 15. Final Capabilities

Users can learn Indian and global finance, ask questions grounded in authoritative sources, request current market/news context, take adaptive quizzes, and understand their simulated portfolio. Finova should behave as a personalized financial tutor, not a generic chatbot.

## 16. Core Principle

We are not training an LLM from scratch. We are engineering a financial AI system around an LLM: LLM + authoritative RAG + multi-agent routing + deterministic tools + live data + memory + evaluation + safety. Everything starts free/local-first, modular, testable and replaceable.

## Primary Indian Sources

SEBI Investor: https://investor.sebi.gov.in/ | SEBI: https://www.sebi.gov.in/ | NISM: https://www.nism.ac.in/ | RBI/DBIE: https://dbie.rbi.org.in/ | NSE: https://www.nseindia.com/ | BSE: https://www.bseindia.com/ | AMFI: https://www.amfiindia.com/ | MCX: https://www.mcxindia.com/ | Income Tax: https://www.incometax.gov.in/
