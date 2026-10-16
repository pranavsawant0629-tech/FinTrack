<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 10: Data Lineage, Source Provenance & Information Lifecycles**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Data Engineering & Regulatory Information Lineage

---

## 1. Where Finova AI's Information Actually Originates

[FACT] Finova AI maintains strict boundaries between six independent data pipelines to ensure zero fabricated numbers and verifiable provenance:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        FINOVA AI DATA SOURCES                          │
├──────────────────────┬────────────────────────┬────────────────────────┤
│  1. REGULATORY RAG   │  2. LIVE MARKET DATA   │  3. CRYPTO DATA        │
│  Official SEBI/NISM  │  NSE/BSE via yfinance  │  CoinGecko Public API  │
│  Investor Booklets   │  Twelve Data Fallback  │  Dual INR / USD Feeds  │
│  (10 PDFs, 283 Chunks)│  Dynamic Session TTL   │  60-Second TTL Cache   │
├──────────────────────┼────────────────────────┼────────────────────────┤
│  4. MARKET NEWS      │  5. EDUCATIONAL QUIZ   │  6. PERSISTENT STATE   │
│  Yahoo Finance RSS   │  Curated Question Bank │  Local SQLite DBs      │
│  Verified Timestamps │  data/quiz/            │  conversations.db      │
│  Headline Attribution│  questions.json        │  memory.db             │
└──────────────────────┴────────────────────────┴────────────────────────┘
```

---

## 2. Deep Dive: The 6 Data Lifecycles

---

### 2.1 Regulatory Knowledge & RAG Grounding (Static Authoritative Corpus)

#### Primary Domain:
`https://investor.sebi.gov.in` (Securities and Exchange Board of India Investor Website)

#### Documents Manifest (`data/manifest.json`):
[FACT] The authoritative vector corpus is restricted to 10 official booklets:
1. `primarymarkets.pdf`: *Beginner's Guide to Primary Market* (IPO process, prospectus, ASBA, book-building).
2. `Secondaryma.pdf`: *Guide to Secondary Markets* (Trading, clearing, settlement cycles, depositories).
3. `MFunds.pdf`: *Introduction to Mutual Funds* (Open-ended vs closed-ended, NAV calculation, expense ratios).
4. `Introduction_to_ETFs.pdf`: *Introduction to Exchange Traded Funds* (Index tracking, creation units, liquidity).
5. `Corporate_Actions_Dividends_Bonus_Splits.pdf`: *Corporate Actions* (Ex-dividend dates, record dates, bonus ratios).
6. `How_to_Buy_and_Sell_Shares_in_Stock_Exchange.pdf`: *Trading Mechanisms* (Demat accounts, brokers, contract notes).
7. `corporatebonds.pdf`: *Fixed Income Securities* (Debentures, coupon rates, credit ratings, yields).
8. `Module_on_Derivative_Segment.pdf`: *Derivatives Segment* (Futures, options, margin requirements, settlement).
9. `igrbrochure.pdf`: *Investor Grievance Redressal (SCORES)* (Lodging complaints, arbitration, timeframes).
10. `dos-and-donts-for-investors-investment-advisers.pdf`: *Do's and Don'ts for Investors* (Risk warnings, RIA verification).

#### Information Lifecycle:
```text
SEBI Server -> Download (scripts/ingest_docs.py) -> data/raw/*.pdf
-> DocumentParser (pypdf text & page extraction)
-> TextChunker (600 chars, 100 overlap)
-> FastEmbed (384-d vector via BAAI/bge-small-en-v1.5)
-> Qdrant Vector Store (data/qdrant_storage/)
-> Cosine Search on User Query (threshold >= 0.65)
-> System Prompt Context Blocks
-> LLM Synthesis
-> CitationValidator (Verifies doc_id & page numbers)
-> UI CitationCards with direct SEBI download links
```

---

### 2.2 Live Equity Market Data (Dynamic Real-Time Feeds)

#### Primary Provider:
`yfinance` Python library querying Yahoo Finance quote APIs for Indian securities (NSE: `.NS`, BSE: `.BO`).

#### Secondary Fallback:
Twelve Data REST API adapter (`TwelveDataProvider`), utilized if Yahoo Finance times out.

#### Data Provided:
- Last Traded Price (LTP) in Indian Rupees (`₹`).
- 24-hour absolute change and percentage change.
- Day High, Day Low, and Trading Volume.
- Previous Trading Day Close.
- Exchange Trading Session (`OPEN`, `CLOSED`, `WEEKEND`, `HOLIDAY`).

#### Freshness & Caching Invariant:
- **During Live Market Hours (09:15–15:30 IST)**: In-memory TTL is strictly **15 seconds**.
- **After-Hours / Weekends**: In-memory TTL extends to **12 hours** to eliminate wasteful network traffic.
- **Provider Outage / Stale Fallback**: If upstream calls fail, `MarketDataCache` serves the last known quote with `is_stale=True`, rendered in the UI with an amber `[STALE DATA]` indicator.

---

### 2.3 Cryptocurrency Market Analytics

#### Provider:
CoinGecko Public REST API (`https://api.coingecko.com/api/v3/simple/price`).

#### Data Provided:
- Real-time prices for major digital assets (Bitcoin, Ethereum, Solana, USDT, Dogecoin, XRP, Cardano, BNB).
- Dual-currency conversion: Price in **INR (₹)** and **USD ($)**.
- 24-hour market price change percentage.

#### Freshness & Outage Handling:
- Caching: 60-second TTL in `CryptoDataService`.
- Outage Fallback: [FACT - Phase 4 Hardening] `CoinGeckoProvider` **strictly raises `CryptoProviderError`** on network failure. Sandbox fallback pricing is **disabled by default** (`allow_offline_fallback=False`) and only activated in isolated unit tests carrying a fixed historic timestamp (`2024-01-01T00:00:00Z`) so live users are never shown fictional test prices.

---

### 2.4 Market News & Headlines

#### Providers:
1. Yahoo Finance News Feeds (`yfinance.Ticker.news`).
2. RSS Feeds from major Indian financial dailies.

#### Data Provided:
- Article Headline.
- Publisher / News Agency Name (e.g. Reuters, Mint, Economic Times).
- Publication Timestamp (ISO 8601).
- Direct External Article Link.

#### Invariant:
The LLM never writes or summarizes financial news without source attribution. Headlined articles are displayed as distinct `NewsCard.tsx` items.

---

### 2.5 Educational Quiz Question Bank (`data/quiz/questions.json`)

#### Origin:
Curated internal question bank covering Indian financial literacy topics:
- Equities & Secondary Markets
- Mutual Funds & Compounding
- Futures & Options Risk
- Primary Markets & IPOs
- Investor Rights & SCORES Grievances

#### Data Structure:
```json
{
  "id": "q_ipo_01",
  "topic": "Primary Markets",
  "question": "What does ASBA stand for in the context of an IPO application?",
  "options": [
    "Application Supported by Blocked Amount",
    "Automated Stock Buying Account",
    "Asset Secured Banking Agreement",
    "Allotment System for Buying Assets"
  ],
  "correct_index": 0,
  "explanation": "ASBA stands for Application Supported by Blocked Amount. Money stays in your bank account until shares are allotted."
}
```

---

### 2.6 Local User Identity & Session History

#### Storage Engines:
- **`data/conversations.db`**: Local SQLite database storing conversation sessions, message transcripts, and UI metadata.
- **`data/memory.db`**: Local SQLite database storing learner profiles (`learning_level`, `risk_profile`) with PII filtering.
- **Client `localStorage`**: Stores browser `user_id` (UUID v4) and display name.

#### Data Invariant:
**Zero Cloud Leakage**. No user conversations, IDs, or profile attributes are transmitted to remote servers. All persistence is isolated on the user's local disk.
