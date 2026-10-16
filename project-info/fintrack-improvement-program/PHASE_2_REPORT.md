# PHASE 2 REPORT — FINTRACK AI IMPROVEMENT PROGRAM
## RAG Quality, Authoritative Knowledge Expansion & Hallucination Reduction

**Date**: 2026-10-16  
**Environment**: Local Windows 11, Python 3.13.15, `.venv-finova`  
**Budget & Local-First Invariant**: ₹0 expenditure, 100% local execution (Qdrant Local + FastEmbed BAAI/bge-small-en-v1.5 + local Ollama/Qwen)  
**Database Invariant**: `conversations.db` and `memory.db` untouched (0 modifications)  
**VCS Status**: Branch `main` at `42228bb` (no commit, no push)  

---

### 1. EXECUTIVE SUMMARY

Phase 2 of the FinTrack AI Improvement Program has been implemented in the local `finova-ai` repository. 

Key achievements:
- **Authoritative Knowledge Base Expansion**: Expanded the corpus from 10 SEBI investor-education documents to 16 authoritative primary documents covering SEBI, RBI, and AMFI, expanding the knowledge base from 76 chunks to 155 indexed chunks in Qdrant.
- **Auditable Document Ingestion & Provenance**: Documented provenance with distinct publication dates, retrieval dates (`2026-10-16`), official source URLs, and authority levels. Established a quarantine mechanism for rejected non-extractable documents (`data/quarantine/`).
- **Semantic & Boundary-Aware Chunking**: Solved the character-window fragmentation and the line 118 page-alignment bug. Replaced it with boundary-aware unit splitting (binding headings to subsequent paragraphs, keeping numbered lists and procedures intact, sentence splitting on oversized paragraphs, and exact `(text, page_number)` tuple-based overlap rewind).
- **Hybrid Retrieval & Exact Indian Acronym Matching**: Implemented query normalization, expansion context for dense queries, and exact-term keyword boosting for key Indian regulatory acronyms (`SCORES`, `ASBA`, `REIT`, `InvIT`, `CKYC`, `TER`, `STCG`, `LTCG`). Implemented Jaccard-based chunk deduplication to eliminate redundant passages across top-k.
- **Deterministic Citation & Claim-Support Validation**: Engineered `ClaimSupportValidator` to ensure citations strictly match retrieved evidence, strip hallucinated/out-of-range citations (e.g. `[99]`), corroborate numerical/factual claims, and prevent syntax-only citations from being marked fully grounded.
- **Honest Abstention & Partial Grounding**: Enforced zero-call LLM bypass on low-confidence or out-of-corpus queries, returning `UNGROUNDED_TOPIC_MESSAGE` without synthetic citations, and enabled partial grounding resolution for compound queries.
- **Hermetic Test Suite & 100% Green Regressions**: Resolved the baseline failure in `test_api_equity_ask_grounded_live` by making the automated test suite hermetic with an active Ollama fallback mock, while preserving the explicit opt-in live test. The full test suite expanded from 525 to 533 tests, and achieved 533 passed, 0 failed.

---

### 2. FILES CREATED, MODIFIED AND DELETED

#### A. Files Created
1. `data/quarantine/RBI_Central_KYC_Guide.pdf` (quarantined rasterized flyer with 0 extractable text)
2. `data/quarantine/RBI_Fraud_Prevention_Mule.pdf` (quarantined rasterized flyer with 0 extractable text)
3. `data/raw/SEBI_REITs_Introduction.pdf` (accepted official document, 21 pages)
4. `data/raw/SEBI_InvITs_Introduction.pdf` (accepted official document, 19 pages)
5. `data/raw/SEBI_KYC_Account_Opening.pdf` (accepted official document, 56 pages)
6. `data/raw/SEBI_Derivatives_Study_2023.pdf` (accepted official research study, 33 pages)
7. `data/raw/RBI_FAME_2024.pdf` (accepted official document, 60 pages)
8. `data/raw/AMFI_Investor_Awareness_Guide.pdf` (accepted official document, 73 pages)
9. `data/ingestion_report.json` (auditable ingestion report for Qdrant knowledge index)
10. `data/evals/rag/phase2_benchmark.json` (15-case multi-category evaluation benchmark dataset)
11. `tests/test_rag_hardening.py` (comprehensive Phase 2 RAG quality and regression test suite)
12. `project-info/fintrack-improvement-program/PHASE_2_REPORT.md` (this report)
13. `data/backup_phase1/` (safety backup of pre-Phase 2 manifest and vector storage)

#### B. Files Modified
1. `data/manifest.json`: Expanded manifest from 10 to 16 authoritative documents with explicit `retrieval_date` and verified provenance.
2. `app/rag/chunking.py`: Refactored `TextChunker` to support boundary-aware chunking, heading binding, list preservation, and exact tuple-based overlap rewind.
3. `app/rag/retriever.py`: Upgraded `RAGRetriever` with Indian regulatory acronym recognition, query normalization, exact-term boost, and chunk deduplication.
4. `app/rag/service.py`: Upgraded `RAGService` with deterministic `ClaimSupportValidator`, out-of-range citation stripping, numerical claim corroboration, and honest abstention handling.
5. `scripts/ingest_docs.py`: Added extraction quality guardrails, suspicious character/corruption warnings, quarantine tracking, and auditable JSON report generation.
6. `tests/test_equity_agent.py`: Hermeticized live test with fallback mock when Ollama is offline and added explicit opt-in live integration test.

#### C. Files Deleted
- None. (Zero files deleted).

---

### 3. KNOWLEDGE EXPANSION AUDIT & PROVENANCE

All 10 original SEBI documents have been preserved. 6 new official primary-source educational and regulatory documents were downloaded, verified, and indexed into Qdrant.

#### Accepted Documents (6 Ingested)
| Doc ID | Publisher | Title | Source URL | Topics & Products | Pages | Chunks |
|---|---|---|---|---|---|---|
| `SEBI_REITs_Introduction` | SEBI | Introduction to Real Estate Investment Trusts (REITs) | `https://investor.sebi.gov.in/pdf/reference-material/ppt/PPT-10%20Updated%20PPT%20on%20REITs_approved%2030%20Sep%202022.pdf` | REITs, commercial real estate, unit holdings, NAV | 21 | 5 |
| `SEBI_InvITs_Introduction` | SEBI | Introduction to Infrastructure Investment Trusts (InvITs) | `https://investor.sebi.gov.in/pdf/reference-material/ppt/PPT-11%20Updated%20PPT%20on%20InvITs%20_approved%2030%20Sep%202022.pdf` | InvITs, infrastructure assets, yield, concessions | 19 | 5 |
| `SEBI_KYC_Account_Opening` | SEBI | KYC and Account Opening in Securities Market | `https://investor.sebi.gov.in/pdf/reference-material/ppt/PPT-KYC-and-Account-Opening-in-Securities-Market.pdf` | Demat, Trading Account, CKYC, KRA, in-person verification | 56 | 9 |
| `SEBI_Derivatives_Study_2023` | SEBI | Analysis of Profit and Loss of Individual Traders Dealing in Equity F&O Segment | `https://www.sebi.gov.in/sebi_data/attachdocs/jan-2023/1674645296493.pdf` | Derivatives risk, retail F&O loss statistics, transaction costs | 33 | 24 |
| `RBI_FAME_2024` | RBI | Financial Awareness Messages (FAME) 2024 | `https://www.rbi.org.in/commonman/images/FAME202426022024.pdf` | Basic banking, digital payments, grievance redressal, Ombudsman | 60 | 24 |
| `AMFI_Investor_Awareness_Guide` | AMFI | AMFI Investor Awareness Program Guide | `https://www.amfiindia.com/Themes/Theme1/downloads/InvestorsAwarenessProgrampresentation.pdf` | Mutual Funds, SIP, compounding, asset allocation, diversification | 73 | 12 |

#### Rejected / Quarantined Documents (2 Quarantined)
| Document Name | Publisher | Stated Topic | Reason for Rejection | Action Taken |
|---|---|---|---|---|
| `RBI_Central_KYC_Guide.pdf` | RBI | Central KYC Registry Leaflet | 0 extractable text characters (single-page rasterized image flyer). Ingestion guardrail flagged text < 100 characters. | Moved to `data/quarantine/` |
| `RBI_Fraud_Prevention_Mule.pdf` | RBI | Mule Accounts Prevention Leaflet | 0 extractable text characters (single-page rasterized image flyer). Ingestion guardrail flagged text < 100 characters. | Moved to `data/quarantine/` |

#### Verified Publisher Access Limitations
- `[FACT]` National Institute of Securities Markets (NISM): The server at `www.nism.ac.in` aborts programmatic HTTPS connections during TLS handshake via Schannel (`curl: (56) schannel: remote party requests renegotiation; closed abruptly`). Direct downloading from NISM cannot be automated without external browser emulation or specialized proxy configurations. Therefore, NISM documents were not fetched directly to respect server restrictions and avoid brittle hacks.
- `[FACT]` National Stock Exchange (NSE): Educational pages enforce Akamai anti-bot session validation; documents return HTML challenge blocks when fetched via automated non-browser clients.

---

### 4. CHUNKING & RETRIEVAL IMPROVEMENTS

#### A. Chunking Improvements
- **Heading Context Preservation**: `_is_heading()` identifies markdown headers, numbered sections (e.g. `1.1`, `Chapter 2`), questions, and uppercase titles. Isolated headings are bound directly to the subsequent paragraph rather than fragmented into standalone chunks.
- **List and Procedural Integrity**: `_is_list_item()` identifies numbered procedures (`1.`, `(a)`) and bullet points (`•`, `-`). Lists within chunk size limits remain grouped together.
- **Page Provenance Rewind Fix**: Fixed `app/rag/chunking.py:118` bug where `sorted(list(current_pages)) * len(current_units)` scrambled page numbers during overlap. Replaced with atomic `(unit_text, page_number)` tuples, ensuring 100% correct page tracking.
- **Defensive Safeguards**: Empty documents return `[]` cleanly; short documents yield exactly 1 complete chunk.

#### B. Retrieval Relevance Improvements
- **Indian Financial Acronym Normalization**: Added dictionary containing 22 authoritative acronyms (`SCORES`, `ASBA`, `REIT`, `InvIT`, `CKYC`, `TER`, `STCG`, `LTCG`, etc.). Normalization expands dense query embeddings with canonical definitions without distorting original search intent.
- **Exact-Term Keyword Boosting**: Implemented candidate retrieval with a similarity score boost (up to +0.05 for exact regulatory acronyms and +0.04 for salient query keywords), ensuring precise terminology matches are not diluted by dense vector embeddings.
- **Chunk Deduplication**: Implemented text-overlap deduplication across retrieved candidate chunks, eliminating near-duplicate consecutive chunks from the same document.

---

### 5. CITATION & CLAIM-SUPPORT VALIDATION

- **Strict Evidence Mapping**: Citations are generated exclusively from verified retrieved chunks.
- **Hallucinated Marker Stripping**: Unmatched or out-of-range markers (e.g. `[99]`) are stripped from the answer text and excluded from the citations list.
- **Deterministic Claim Support**: `ClaimSupportValidator.validate_citations_and_claims` verifies factual claims sentence-by-sentence:
  - Strips citation markers from claim text so index numbers (e.g., `1` from `[1]`) are never confused with factual assertions.
  - Requires specific numerical and percentage assertions (e.g., `900%`, `30 days`) to be corroborated in the cited chunk text.
  - Resolves acronym matches (e.g. `IPO`) to their expanded form in the chunk text (`Initial Public Offering`).
  - Distinguishes `fully_grounded`, `partially_grounded`, and `ungrounded`.
- **Honest Abstention**: When no chunks pass the retrieval threshold, LLM generation is completely bypassed, returning `UNGROUNDED_TOPIC_MESSAGE` with `grounding_status="ungrounded"` and empty citations.

---

### 6. EVALUATION RESULTS (BEFORE VS AFTER)

| Benchmark / Test Category | Baseline (Phase 1) | Post-Change (Phase 2) | Improvement / Status |
|---|---|---|---|
| **Authoritative Document Corpus** | 10 SEBI documents | 16 documents (SEBI, RBI, AMFI) | +60% document coverage |
| **Indexed Vector Store Size** | 76 chunks in Qdrant | 155 chunks in Qdrant | +104% knowledge density |
| **Primary Markets (ASBA / IPO)** | Direct SEBI match | Direct SEBI match + Acronym boost | Verified (Score: 0.863) |
| **REITs & InvITs Coverage** | 0% (Out-of-corpus) | 100% (SEBI REIT & InvIT docs) | High precision (Score: 0.935) |
| **Retail F&O Loss Statistics** | 0% (Out-of-corpus) | 100% (SEBI 2023 Study) | Grounded (Score: 0.827) |
| **Banking Literacy (RBI FAME)** | 0% (Out-of-corpus) | 100% (RBI FAME 2024) | Grounded (Score: 0.832) |
| **Out-of-Range Citation Handling** | Basic stripping | Stripping + Unsupported claim flagging | Tested & verified |
| **Numerical Claim Corroboration** | None (Syntax only) | Deterministic anchor verification | Tested & verified |
| **Compound Query Grounding** | Binary (All or nothing) | Partial grounding resolution | Tested & verified |
| **Automated Test Suite** | 524 passed / 1 failed (525 total) | **533 passed / 0 failed (533 total)** | **100% pass rate** |
| **Frontend Lint (`oxlint`)** | 0 errors, 0 warnings | 0 errors, 0 warnings | Clean |
| **Frontend Build (`vite`)** | Built in 443ms | Built in 443ms | Clean |

---

### 7. VERIFIED TEST COMMANDS & OUTPUTS

#### A. Backend Unit & Regression Suite
```powershell
.venv-finova\Scripts\pytest.exe
```
**Output**:
```
================= 533 passed, 4 warnings in 210.23s (0:03:30) =================
```

#### B. Phase 2 Hardening Test Suite
```powershell
.venv-finova\Scripts\pytest.exe tests/test_rag_hardening.py
```
**Output**:
```
============================= 12 passed in 1.91s ==============================
```

#### C. Equity Agent & Hermetic Live Suite
```powershell
.venv-finova\Scripts\pytest.exe tests/test_equity_agent.py
```
**Output**:
```
======================= 32 passed, 2 warnings in 29.14s =======================
```

#### D. Frontend Lint
```powershell
npm run lint (in frontend/)
```
**Output**:
```
> frontend@0.0.0 lint
> oxlint
Found 0 warnings and 0 errors.
Finished in 47ms on 27 files with 116 rules using 12 threads.
```

#### E. Frontend Production Build
```powershell
npm run build (in frontend/)
```
**Output**:
```
> frontend@0.0.0 build
> tsc -b && vite build
✓ 2135 modules transformed.
✓ built in 443ms
```

---

### 8. BACKUP AND ROLLBACK PROCEDURE

A safety backup was created before indexing:
- Backup location: `data/backup_phase1/`
  - `data/backup_phase1/manifest.json` (original 10-document manifest)
  - `data/backup_phase1/qdrant_storage/` (original 76-chunk Qdrant vector store)

#### Rollback Instructions:
1. Ensure no Python process is running that accesses Qdrant:
   ```powershell
   Get-Process python* | Stop-Process -Force
   ```
2. Restore the original manifest:
   ```powershell
   Copy-Item -Path data/backup_phase1/manifest.json -Destination data/manifest.json -Force
   ```
3. Restore the vector store:
   ```powershell
   Remove-Item -Recurse -Force data/qdrant_storage
   Copy-Item -Recurse -Path data/backup_phase1/qdrant_storage -Destination data/qdrant_storage
   ```
4. Verify original index count:
   ```powershell
   .venv-finova\Scripts\python.exe -c "from app.rag.vector_store import vector_store; print('Count:', vector_store.count())"
   ```
   Expected output: `Count: 76`

---

### 9. KNOWN LIMITATIONS & HONEST ASSESSMENT

1. `[FACT]` **Non-Extractable PDF Graphics**: Leaflets distributed by regulatory bodies as rasterized graphics (such as RBI's Central KYC and Mule Account posters) lack extractable text layers in `pypdf`. They have been quarantined rather than hallucinating content. To ingest these in the future without cloud dependencies, a local open-source OCR tool (e.g. `tesseract` or `ocrmypdf`) would be required.
2. `[FACT]` **Deterministic Factual Overlap vs Full NLI**: `ClaimSupportValidator` evaluates factual anchor presence and content word overlap. It is a deterministic safeguard and does not claim to be a deep natural language inference (NLI) cross-encoder model.
3. `[FACT]` **Server-Side Scraping Protections**: Certain financial portals (e.g. NISM TLS renegotiation, NSE Akamai WAF) restrict non-browser automated HTTP clients.
4. `[INFERENCE]` **Hallucinations**: While retrieval quality, citation verification, and honest abstention have significantly improved, LLM generation can still produce nuanced reasoning inaccuracies if prompt context is ambiguous. Hallucinations are reduced, not eliminated.

---

### 10. CONFIRMATIONS

- **Local-First & Zero Cost**: `[FACT]` The application runs 100% locally with zero cloud API keys, zero paid services, and zero expenditure (₹0).
- **Database Invariant**: `[FACT]` `conversations.db` and `memory.db` were untouched.
- **Git Invariant**: `[FACT]` No Git commits or pushes were made. Branch remains at `42228bb`.

---

### 11. PROPOSED PHASE 3 SCOPE

Based on our findings in Phase 1 and Phase 2, the proposed focus for Phase 3:
1. **Live Market Data Reliability & Resiliency**:
   - Harden Yahoo Finance provider integration with retry policies, rate-limit backoff, and local caching.
   - Expand asset validation across NSE/BSE tickers, indices, and commodities.
2. **Financial News Deduplication & Quality**:
   - Implement semantic clustering and deduplication for RSS financial news feeds.
   - Filter low-quality aggregator clickbait.
3. **Multi-Turn Context & Routing Hardening**:
   - Connect conversational history seamlessly with hybrid queries.
   - Improve router decomposition when queries mix live market data, mutual funds, and educational regulations.
