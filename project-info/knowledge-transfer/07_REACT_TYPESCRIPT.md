<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 07: React 19 & TypeScript Frontend Architecture**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Frontend Software Engineering & Component Hierarchy

---

## 1. Modern React 19 & TypeScript Foundations

### 1.1 Declarative Component Architecture
[FACT] The Finova AI user interface is built on **React 19** and **TypeScript 5.9+**. 
- In imperative programming, developers manually select DOM nodes and manipulate styles (`document.getElementById().innerHTML = ...`).
- In React's **declarative model**, components are pure functions of state: `UI = f(State)`. When state changes, React computes a virtual DOM diff and updates the physical DOM efficiently.

### 1.2 TypeScript Contracts & Type Safety
[FACT] Every property (`props`), hook return value, and API payload is strictly typed via TypeScript interfaces declared in [frontend/src/api/types.ts](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/api/types.ts).
- Eliminates `undefined is not a function` runtime crashes.
- Enforces 1-to-1 parity between backend Pydantic models (`OrchestratorResponse`) and frontend interfaces (`OrchestratorResponse`).

### 1.3 Tailwind CSS v4 & The "Marigold Field" Design Tokens
[FACT] Finova AI utilizes **Tailwind CSS v4** with a custom editorial design system declared in [frontend/src/index.css](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/index.css):
- `--color-marigold`: Warm gold accent (`#e5a93b`) representing wealth and financial optimism.
- `--color-terracotta`: Earthy rust (`#c85a32`) for risk warnings, derivatives, and crypto cards.
- `--color-teal`: Deep sea green (`#2a8f82`) for equity gains and authoritative regulatory citations.
- Glassmorphism: `backdrop-blur-md`, subtle border glows (`border-white/10`), and dark mode contrast tokens.

---

## 2. End-to-End User Interaction Trace

[FACT] Below is the complete trace of an interaction when a user submits a question in the UI:

```text
1. USER TYPES & CLICKS SUBMIT
   User types "What is the price of TCS?" into ChatInput and presses Enter.
   │
   ▼
2. REACT EVENT HANDLER
   `ChatInput.tsx` catches `onSubmit` event, prevents default form reload (`e.preventDefault()`),
   and invokes `onSendMessage(input)`.
   │
   ▼
3. STATE UPDATE & OPTIMISTIC RENDERING (`useChat.ts`)
   - Generates temporary user message: `{ role: 'user', content: 'What is the price of TCS?' }`.
   - Appends to `messages` state array -> `MessageList.tsx` renders user bubble instantly.
   - Sets `isLoading = true` -> `LoadingBubble.tsx` mounts and begins elapsed-time counter.
   │
   ▼
4. API CLIENT DISPATCH (`api/client.ts`)
   `apiClient.sendMessage({ message, conversation_id, user_id, domain_context })`
   Constructs standard `fetch()` HTTP request to `http://127.0.0.1:8000/chat`.
   │
   ▼
5. NETWORK TRANSPORT (HTTP REST)
   Browser emits POST request with JSON payload over local TCP connection (port 8000).
   │
   ▼
6. FASTAPI & MULTI-AGENT BACKEND EXECUTION
   FastAPI validates schema -> Safety checks regex -> Central Router routes to Equity Agent
   -> Yahoo Finance fetches quote -> ResponseComposer packages JSON -> Returns 200 OK.
   │
   ▼
7. PROMISE RESOLUTION IN FRONTEND
   `useChat.ts` receives HTTP 200 JSON response object (`OrchestratorResponse`).
   │
   ▼
8. FINAL STATE SETTLEMENT
   - Sets `isLoading = false` -> `LoadingBubble` unmounts.
   - Appends assistant message with attached `market_quotes` and `citations` metadata.
   - Persists updated `conversation_id` in browser state.
   │
   ▼
9. COMPONENT RE-RENDER
   `MessageItem.tsx` detects `market_quotes` array -> Mounts `MarketQuoteCard.tsx`.
   The learner sees the natural language explanation alongside the live quote chip.
```

---

## 3. Core Component Walkthrough

---

### File: `frontend/src/App.tsx`
1. **Path**: [frontend/src/App.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/App.tsx)
2. **Role**: Top-level layout container and master state orchestrator.
3. **Key State Variables**:
   - `isSidebarOpen: boolean`: Controls mobile sidebar overlay visibility.
   - `isProfileOpen: boolean`: Controls Profile & Memory modal display.
   - `activeSection: TutorSectionId`: Active learning subject (e.g. `'equity'`, `'derivatives'`).
4. **Hooks Used**: `useChat`, `useIdentity`, `useTheme`.
5. **Layout Structure**:
   - Left: Fixed/collapsible `Sidebar.tsx`.
   - Top: Global `Header.tsx`.
   - Center: `TutorLanding.tsx` (if zero messages) or `MessageList.tsx` + `ChatInput.tsx`.

---

### File: `frontend/src/components/layout/Sidebar.tsx`
1. **Path**: [frontend/src/components/layout/Sidebar.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/layout/Sidebar.tsx)
2. **Role**: Subject navigation and conversation thread manager.
3. **Core Features**:
   - **Tutor Subject Navigation**: 9 dedicated buttons (`General Chat`, `Equity Tutor`, `Derivatives Tutor`, `Personal Finance`, `Crypto Tutor`, `Portfolio Tutor`, `Market News`, `Quiz & Challenge`, `System Guide`).
   - **Date Grouping**: Groups past chat sessions into `TODAY`, `YESTERDAY`, `PREVIOUS 7 DAYS`, and `OLDER`.
   - **Inline Thread Actions**: Enables renaming conversation titles (`Edit2` icon) and hard deletion (`Trash2` icon) with optimistic state cleanup.

---

### File: `frontend/src/components/chat/MessageItem.tsx`
1. **Path**: [frontend/src/components/chat/MessageItem.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/chat/MessageItem.tsx)
2. **Role**: Renders an individual conversation turn (user or assistant).
3. **Key Subcomponents Rendered Dynamically**:
   - `ReactMarkdown`: Parses assistant markdown (headers, bullet points, bold text).
   - `GroundingBadge.tsx`: Emits green (`fully_grounded`), amber (`partially_grounded`), or gray (`ungrounded`) badge.
   - `MarketQuoteCard.tsx`: Rendered if `metadata.market_quotes` has items.
   - `PayoffTableCard.tsx`: Rendered if `metadata.payoff_table` is present.
   - `PortfolioCard.tsx`: Rendered if `metadata.portfolio` is present.
   - `QuizCard.tsx`: Rendered if `metadata.quiz` is present.
   - `CitationCard.tsx`: Rendered if `metadata.citations` has items.
   - `LearningActions.tsx`: Action buttons below the response (e.g. *"Take a Quiz on this topic"*).
   - `RelatedConcepts.tsx`: Clickable pills for topic continuity.

---

### File: `frontend/src/components/chat/LoadingBubble.tsx`
1. **Path**: [frontend/src/components/chat/LoadingBubble.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/chat/LoadingBubble.tsx)
2. **Role**: Provides honest user feedback while the local LLM generates responses.
3. **Design Decision**: Rather than showing fake progress bars (e.g. "Step 1: Reading web... Step 2: Analyzing..."), it runs a live elapsed-time counter (`Elapsed: 4.2s`). Because local 7B inference on consumer GPUs takes 2–15 seconds, honest timing sets proper user expectations without deception.

---

### File: `frontend/src/components/cards/PayoffTableCard.tsx`
1. **Path**: [frontend/src/components/cards/PayoffTableCard.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/cards/PayoffTableCard.tsx)
2. **Role**: Interactive visual table for options contracts.
3. **Displays**:
   - Header: Option Type (`CALL` / `PUT`), Position (`LONG` / `SHORT`), Strike Price, Premium.
   - Summary Stats: Calculated Breakeven price, Maximum Profit (`Unlimited` or capped), Maximum Loss.
   - Table: Scrollable 21-row table mapping sample underlying spot prices to net profit/loss in green (`+₹`) or red (`-₹`).

---

### File: `frontend/src/components/cards/QuizCard.tsx`
1. **Path**: [frontend/src/components/cards/QuizCard.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/cards/QuizCard.tsx)
2. **Role**: Interactive quiz challenge interface.
3. **State & Behavior**:
   - Allows learner to click an option (`A`, `B`, `C`, `D`).
   - Learner clicks "Submit Answer".
   - Client-side grading highlights correct answer in green and incorrect answer in red.
   - Reveals comprehensive pedagogical explanation text immediately.

---

### File: `frontend/src/components/memory/ProfileModal.tsx`
1. **Path**: [frontend/src/components/memory/ProfileModal.tsx](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/components/memory/ProfileModal.tsx)
2. **Role**: User privacy audit and settings dialog.
3. **Displays**:
   - Persistent User ID (UUID) stored in client `localStorage`.
   - Editable Display Name.
   - Table of active memory items recorded by the backend (`learning_level: beginner`, `risk_profile: conservative`).
   - "Clear Memory" button: Invokes `DELETE /memory?user_id=...` to permanently purge records.

---

## 4. Custom Hooks Architecture

---

### Hook: `useChat.ts`
- **Location**: [frontend/src/hooks/useChat.ts](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/hooks/useChat.ts)
- **Role**: Master chat state machine managing:
  - `messages: Message[]`: Active turn array.
  - `isLoading: boolean`: In-flight request status.
  - `error: string | null`: Error message state.
  - `sendMessage(text, domain)`: Optimistic dispatch and network error handling.
  - `loadConversation(id)`: Fetches thread history when clicking sidebar items.
  - `resetChat()`: Clears active turn state for a new chat.

---

### Hook: `useIdentity.ts`
- **Location**: [frontend/src/hooks/useIdentity.ts](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/hooks/useIdentity.ts)
- **Role**: Client-side identity provider.
- **Behavior**:
  - Inspects `localStorage.getItem("finova_user_id")`.
  - If null, generates a fresh random UUID v4 (`crypto.randomUUID()`) and saves it.
  - Manages `displayName` (defaults to `"Learner"`).

---

### Hook: `useTheme.ts`
- **Location**: [frontend/src/hooks/useTheme.ts](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/frontend/src/hooks/useTheme.ts)
- **Role**: Controls color scheme preferences.
- **Behavior**:
  - Persists preference (`"dark"` or `"warm"`) in `localStorage`.
  - Toggles the `.dark` class on the root `document.documentElement` element to switch CSS variable definitions.
