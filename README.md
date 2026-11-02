# Sentinel Chatbot 🛡️

**Enterprise Customer Support & Multimodal Knowledge Intelligence Platform**

Sentinel Chatbot is a modular, high-reliability enterprise conversational system featuring real-time multilingual sentiment analysis, automated ticket lifecycle and SLA management, production knowledge base pipelines with quality gates, RAG-based factual assistance with temporal policy resolution, multimodal file verification with PII masking, and multi-turn multilingual conversational memory.

For an in-depth technical analysis, architecture diagrams, and tech stack rationale, see [IMPLEMENTATION.md](file:///Users/anand/Documents/Sentinel%20Chatbot/IMPLEMENTATION.md).

---

## Subsystems

1. **Multilingual Sentiment Analysis & Escalation Engine** (`src/sentiment/`)
   - 6-class sentiment classification (`positive`, `neutral`, `negative`, `frustrated`, `urgent`, `sarcastic`).
   - Sarcasm detection & calm high-risk issue detection (account compromise, fraud, duplicate payments).
   - Dynamic after-hours routing (urgent $\rightarrow$ on-call queue; normal $\rightarrow$ next business day).
   - 15-minute unresolved negative conversation auto-escalation.
   - Policy-preserving tone adjustment.

2. **Support Ticket Management & SLA Engine** (`src/tickets/`)
   - Structured extraction (customer, order, product, issue, evidence, contact).
   - Mandatory missing field prompting.
   - 5-factor weighted priority calculator (`severity`, `sentiment`, `waiting_time`, `customer_impact`, `sla_urgency`).
   - Routing by team skills, agent workload limits (max 10), and fallback to general queue.
   - Calendar-aware SLA tracking excluding weekends and holidays, 75% warning trigger, breach escalation.
   - Duplicate ticket detection and PII-masked agent handoff summaries.

3. **Knowledge Base Production Pipeline** (`src/knowledge_pipeline/`)
   - Incremental ingestion, SHA-256 deduplication, quarantine of invalid/corrupt/injected files.
   - Version history tracking with atomic rollback.
   - Pre-deployment quality gates (accuracy $\ge 0.85$, grounding $\ge 0.80$).
   - Scheduled updates within maintenance windows (01:00 AM – 05:00 AM).
   - Exponential retry engine (15m, 30m, 60m).
   - Post-deployment health monitoring with 5-minute automatic rollback on failure.
   - Role-Based Access Control (RBAC) with full audit logging.

4. **RAG Knowledge Assistant** (`src/rag/`)
   - Metadata storage: product, region, access level, effective date, expiry date.
   - Temporal policy resolution: filters active policies for current queries; retrieves historical policies by date.
   - Conflict resolution selecting the latest applicable version.
   - Mandatory source citations in every answer.
   - Refusal on missing evidence and detection of unsupported claims.
   - Defense against prompt injection in queries and embedded document instructions.

5. **Multimodal File Processing Engine** (`src/multimodal/`)
   - Multi-format validation: images, PDFs, invoices, receipts, screenshots.
   - Extraction of order IDs, dates, amounts, product codes, error codes.
   - Discrepancy cross-referencing between customer statements and document figures.
   - Automatic offloading to background queue if processing takes $> 30$ seconds.
   - Automatic deletion of customer files upon 72-hour retention expiry.
   - PII and payment data masking across all logs.

6. **Multilingual Support & Session Management** (`src/multilingual/`)
   - Native support for English (`en`), Spanish (`es`), French (`fr`), and Hindi (`hi`).
   - Mixed-language utterances (code-switching) and transliterated Hindi (Romanized script).
   - Typo and spelling error correction.
   - 10-turn conversational context retention, language switching, and self-correction handling.
   - 30-minute inactivity timeout.
   - 24-hour session recovery with conversation summary restoration.

---

## Running the Platform

### Run All 75 Automated Tests:
```bash
/Library/Developer/CommandLineTools/usr/bin/python3 scripts/run_all_tests.py
```

### Run the End-to-End Live Demonstration:
```bash
/Library/Developer/CommandLineTools/usr/bin/python3 scripts/demo_all_subsystems.py
```

