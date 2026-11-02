# Sentinel Chatbot 🛡️

**Enterprise AI Customer Support & Multimodal Operations Platform**

Sentinel Chatbot is a modern, full-stack browser-based customer support SaaS platform built around a high-reliability conversational intelligence engine. It features real-time multilingual sentiment analysis, automated ticket lifecycle and calendar-aware SLA routing, production knowledge base pipelines with automated quality gates, verifiable RAG with temporal policy resolution, multimodal OCR invoice extraction with PII redaction, and multi-turn conversational session memory.

For an in-depth technical analysis and architecture diagrams, see [IMPLEMENTATION.md](file:///Users/anand/Documents/Sentinel%20Chatbot/IMPLEMENTATION.md).

---

## Web Application Architecture

```
Sentinel Chatbot/
├── backend/                           # FastAPI REST API & Database Layer
│   ├── main.py                        # FastAPI application, CORS, lifecycle, static mount
│   ├── config.py                      # Database, upload, security settings
│   ├── database.py                    # SQLAlchemy session and engine
│   ├── models.py                      # SQLAlchemy ORM models (Conversation, Ticket, Document, etc.)
│   ├── schemas.py                     # Pydantic v2 validation models
│   ├── service.py                     # Bridge to core Sentinel Chatbot engine
│   └── routers/                       # Modular FastAPI route controllers
│       ├── chat.py                    # Inbound chat & multimodal file uploads
│       ├── tickets.py                 # Support ticket lifecycle & internal notes
│       ├── knowledge.py               # Policy document ingestion & quality gates
│       ├── analytics.py               # Live operational telemetry & trend metrics
│       ├── admin.py                   # Runtime configuration settings
│       └── health.py                  # Health check & subsystem diagnostics
├── frontend/                          # Modern React 18 + TypeScript + Vite UI
│   ├── src/
│   │   ├── components/                # Sidebar, Navbar, SentimentBadge, PriorityBadge, StatusBadge
│   │   ├── pages/                     # Dashboard, Live Chat, Tickets, Knowledge, Analytics, Settings
│   │   ├── api/client.ts              # Typed API communication client
│   │   └── types/index.ts             # Shared frontend data models
│   ├── tailwind.config.js             # Modern Tailwind theme with dark mode
│   └── vite.config.ts                 # Vite bundler with /api proxy
├── src/                               # Core Sentinel Chatbot Engine (6 Subsystems)
│   ├── sentiment/                     # 6-class sentiment, sarcasm, calm high-risk escalations
│   ├── tickets/                       # Structured extraction, priority scoring, calendar SLA
│   ├── knowledge_pipeline/            # Ingestion, SHA-256 deduplication, quality gates, quarantine
│   ├── rag/                           # Metadata indexing, temporal policy resolution, citations
│   ├── multimodal/                    # OCR extraction, discrepancy detection, 72h retention
│   ├── multilingual/                  # en/es/fr/hi, code-switching, transliteration, sessions
│   └── chatbot.py                     # SentinelChatbot unified orchestrator
├── tests/                             # Comprehensive test suites (83 tests)
└── scripts/
    ├── run_all_tests.py               # Automated test runner (100% pass rate)
    └── demo_all_subsystems.py         # Subsystems live demonstration script
```

---

## Quickstart & Execution Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+ & npm

### 1. Installation

#### Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

#### Frontend Setup
```bash
# Navigate to frontend and install packages
cd frontend
npm install
```

---

### 2. Running Locally (Two Terminals)

#### Terminal 1 — FastAPI Backend:
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs (Swagger UI): **`http://127.0.0.1:8000/docs`**
- API Health Status: **`http://127.0.0.1:8000/api/health`**

#### Terminal 2 — React Frontend:
```bash
cd frontend
npm run dev
```
- Browser Web App: **`http://localhost:5173`**

*(Note: If you run `npm run build` in `frontend/`, the FastAPI backend will also automatically serve the compiled production web app directly on `http://127.0.0.1:8000`)*.

---

## Core Application Modules & Views

1. **Operations Dashboard** (`/`):
   - Real-time KPIs: Inbound Conversations, Active Sessions, Support Tickets, Escalations, High-Risk Alerts, Latency.
   - Interactive 7-Day Conversation Activity timeline & Sentiment breakdown.
   - Recent escalations and live tickets queue.

2. **Live Customer Chat** (`/chat`):
   - Real-time customer chat interface powered by `SentinelChatbot.handle_message()`.
   - Live multi-class sentiment detection (`positive`, `neutral`, `negative`, `frustrated`, `urgent`, `sarcastic`).
   - Sarcasm detection and calm high-risk escalation triggers.
   - Verified source citations on every factual answer.
   - Multimodal drag-and-drop file upload for invoices, receipts, and images with OCR extraction.
   - Right-side Conversation Intelligence Inspector.

3. **Support Ticket Management** (`/tickets`):
   - Automated ticket creation from escalations with 5-factor priority calculation.
   - Calendar-aware SLA tracking excluding configured weekends and holidays with 75% warning trigger.
   - Team assignment (`billing`, `technical`, `account_security`, `shipping`, `general`).
   - Interactive status updates (`Open`, `In Progress`, `Pending`, `Escalated`, `Resolved`, `Closed`).
   - Confidential internal notes timeline for agent collaboration.

4. **Knowledge Base Management** (`/knowledge`):
   - Document upload with automated quality gate testing (Accuracy $\ge 0.85$, Grounding $\ge 0.80$).
   - Automatic security quarantine for prompt-injection attacks.
   - Role-Based Access Control tiers (`public`, `internal`, `restricted`, `confidential`).
   - Temporal version indexing for historical and current policy queries.

5. **Operational Telemetry & Analytics** (`/analytics`):
   - Ticket resolution rates and escalation ratios.
   - Multilingual query distribution (English, Spanish, French, Hindi).
   - Team workload capacity and priority distribution.

6. **System Administration** (`/settings`):
   - Operating business hours configuration.
   - SLA response threshold tuning per priority.
   - Escalation trigger threshold sliders.
   - Subsystem diagnostics and maintenance window controls.

---

## Running the Automated Test Suite

Sentinel Chatbot includes an automated test suite with **83 unit and integration tests** verifying all 6 subsystems and the FastAPI backend APIs:

```bash
./.venv/bin/python scripts/run_all_tests.py
```

### Test Results:
- **Total Tests Run**: 83
- **Pass Rate**: 100% (83 Passing, 0 Failures, 0 Errors)
- **Execution Time**: ~0.10s

