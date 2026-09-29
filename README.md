# 🧠 Vera: AI Feedback Intelligence Agent
> **AI-powered product feedback analysis with Hindsight long-term memory.**  
> *Built for HackwithHyderabad 3.0 • Track: Agentic Memory & Reasoning*

---

## 🌟 Overview: The Problem & The Solution

Every product team collects hundreds of user complaints, bug reports, and suggestions across support tickets, in-app widgets, App Store reviews, and user interviews.

Traditional LLM assistants have a major flaw: **they have amnesia**.
- When you ask a standard LLM agent *"What's broken?"*, it only sees whatever data is stuffed into the immediate context window.
- It cannot tell you **when a problem started**, whether latency escalated into a fatal error, or if customer complaints dropped after a recent release.

### 💡 The Solution: Hindsight Long-Term Memory
By integrating **Hindsight** (`hindsight-all`), our Feedback Intelligence Agent remembers every customer interaction across weeks and months:
1. **Retains & Indexes:** Feedback is tagged with product areas (`pdf_upload`, `login`, `billing`), sources (`support_ticket`, `in_app_feedback`), and original timestamps.
2. **Consolidates Observations:** Automatically connects recurring patterns across time (e.g., *"PDF upload latency in Jan became connection timeouts in March"*).
3. **Multi-Strategy TEMPR Recall:** Retrieves memories using parallel semantic search, BM25, entity knowledge graphs, and temporal extraction.
4. **Verifiable Evidence Citations:** Answers questions citing verbatim quotes, dates, and channels — completely eliminating hallucinations.

---

## 🏗️ Architecture

```
                               ┌───────────────────────────────────────────────┐
                               │             CLIENT BROWSER (UI)               │
                               │  Jinja2 + Tailwind CSS + HTMX + Alpine.js     │
                               └──────────────────────┬────────────────────────┘
                                                      │ HTTP / HTMX
                                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FASTAPI BACKEND (port 8000)                                    │
│                                                                                                      │
│   ┌───────────────────────────┐         ┌─────────────────────────┐                                  │
│   │       PAGE ROUTES         │         │        API ROUTES       │                                  │
│   │  /           (Home)       │         │  POST /api/feedback     │                                  │
│   │  /demo       (Guided Demo)│         │  POST /api/import       │                                  │
│   │  /ask        (Chat Agent) │         │  POST /api/ask          │                                  │
│   │  /dashboard  (Analytics)  │         │  GET  /api/stats        │                                  │
│   │  /feedback   (Submit Form)│         │  GET  /api/trends       │                                  │
│   │  /import     (CSV/JSON)   │         │  GET  /api/feedback/rec │                                  │
│   └─────────────┬─────────────┘         └────────────┬────────────┘                                  │
│                 │                                    │                                               │
│                 └─────────────────┬──────────────────┘                                               │
│                                   ▼                                                                  │
│                     ┌───────────────────────────┐                                                    │
│                     │      SERVICE LAYER        │                                                    │
│                     │  • FeedbackService        │                                                    │
│                     │  • AgentService           │                                                    │
│                     └─────────────┬─────────────┘                                                    │
│                                   │                                                                  │
│                                   ▼                                                                  │
│                     ┌───────────────────────────┐                                                    │
│                     │     HINDSIGHT ENGINE      │                                                    │
│                     │   (Embedded in-process)   │                                                    │
│                     │  Bank: feedback-intell    │                                                    │
│                     │  • Vector Embeddings      │                                                    │
│                     │  • Temporal Indexing      │                                                    │
│                     │  • Cross-Encoder Rerank   │                                                    │
│                     │  • Observation Graph      │                                                    │
│                     └───────────────────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Git

### 2. Clone & Install
```bash
git clone <repo-url>
cd feedback-intelligence
pip install -r requirements.txt
```

### 3. Configure `.env`

**Option A: Local Demo Mode (Default - Fast, No API Key Needed)**
```env
# Hindsight Bank Configuration
HINDSIGHT_BANK_ID=feedback-intelligence
HINDSIGHT_LLM_PROVIDER=openai
HINDSIGHT_LLM_MODEL=gpt-4o-mini
HINDSIGHT_LLM_API_KEY=sk-dummy-key-for-local-testing

# OpenAI Configuration
OPENAI_API_KEY=sk-dummy-key-for-local-testing

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Embedded Hindsight server disabled - uses local memory + TEMPR synthesis
HINDSIGHT_EMBEDDED=false
```

> **Note on Dual-Mode Resilience:** In local mode, the application operates in **Interactive Demo Mode**, utilizing the local Hindsight embedding pipeline and built-in TEMPR evidence synthesis so you can test all features offline without any 401 errors!

**Option B: Full Hindsight with OpenAI Codex (ChatGPT Plus/Pro Subscription)**
> Uses your existing ChatGPT Plus/Pro subscription - no separate OpenAI API key needed.

Prerequisites:
```bash
# 1. Install Codex CLI
npm install -g @openai/codex

# 2. Authenticate with your ChatGPT account
codex auth login
# Opens browser → authorize → saves OAuth tokens to ~/.codex/auth.json

# 3. Verify authentication
ls ~/.codex/auth.json  # Should show the auth file exists
```

Then configure `.env`:
```env
# Hindsight Bank Configuration
HINDSIGHT_BANK_ID=feedback-intelligence
HINDSIGHT_LLM_PROVIDER=openai-codex
HINDSIGHT_LLM_MODEL=gpt-4o-mini          # Not used for Codex (has its own default)
HINDSIGHT_LLM_API_KEY=                    # Empty - Codex reads from ~/.codex/auth.json

# OpenAI Codex Configuration
HINDSIGHT_CODEX_MODEL=gpt-5.4-mini        # Default model for Codex provider
CODEX_HOME=.codex                          # Optional: dedicated creds directory

# OpenAI Configuration (for hindsight-litellm wrapper)
OPENAI_API_KEY=                            # Empty - not needed with Codex

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Enable embedded Hindsight server with Codex
HINDSIGHT_EMBEDDED=true
```

**Option C: Full Hindsight with OpenAI API Key (Traditional)**
```env
# Hindsight Bank Configuration
HINDSIGHT_BANK_ID=feedback-intelligence
HINDSIGHT_LLM_PROVIDER=openai
HINDSIGHT_LLM_MODEL=gpt-4o-mini
HINDSIGHT_LLM_API_KEY=sk-your-openai-api-key

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Enable embedded Hindsight server
HINDSIGHT_EMBEDDED=true
```

### 4. Run Application
```bash
# Windows (double-click)
start.bat

# or
python main.py
```

Fast startup (~3 seconds) in local mode. To boot the full embedded Hindsight server (loads ML models, runs DB migrations, requires a valid OpenAI key or Codex auth), set `HINDSIGHT_EMBEDDED=true` in `.env`.

Open your browser at: **`http://localhost:8000`**

---

## 🎬 4-Step Interactive Demo Flow (`/demo`)

Navigate to **`/demo`** in the application to experience the guided 4-step demonstration proving why memory matters:

| Step | Action in UI | What Happens Under the Hood | The Agent's Answer |
| :---: | :--- | :--- | :--- |
| **1** | **Load Recent Feedback (1 Month)** | Retains April 2025 feedback (~50 items). | Baseline established. Agent only knows recent events. |
| **2** | **Query Recent Memory:** *"What are the main problems users are experiencing right now?"* | Recalls April memories only. | Spots that PDF uploads are failing, but **misdiagnoses it as a new sudden outage** because it lacks prior context. |
| **3** | **Expand Memory (4 Months of History)** | Retains Jan, Feb, Mar, and Apr 2025 (~250 items). | Hindsight memory bank grows. Chronological observations consolidate. |
| **4** | **Ask Temporal Reasoning:** *"How has the PDF upload problem changed over time?"* | **The Aha! Moment:** Multi-month TEMPR recall cross-references the entire timeline. | **The Complete Story:**<br>• **Jan:** 30s latency complaints.<br>• **Feb:** Unresolved performance friction.<br>• **Mar:** Update caused timeout errors.<br>• **Apr:** Critical failure blocker.<br>*Bonus:* Notes that Login issues were resolved in April by SAML SSO! |

---

## 📊 Feature Highlights

- **Interactive Demo Walkthrough (`/demo`):** Step-by-step UI with state tracking and Before/After comparison.
- **Natural Language Inquiry (`/ask`):** Chat interface with suggestion chips, memory citations, and verbatim evidence.
- **Real-Time Intelligence Dashboard (`/dashboard`):** Aggregated metrics across product areas, channel distribution, and sentiment shift trends.
- **Direct Feedback Submission (`/feedback`):** Real-time retention with entity and module tagging.
- **Bulk CSV / JSON Ingestion (`/import`):** Upload historical datasets with schema validation.
- **Zero-Crash Resilience:** Graceful fallbacks for seamless presentation without third-party API downtime.

---

## 📁 Project Structure

```
feedback-intelligence/
├── config.py                 # Pydantic settings & bank configuration
├── main.py                   # FastAPI server, lifespan & dual HTMX/JSON routes
├── requirements.txt          # Python dependencies
├── .env                      # Environment configuration
├── data/                     # Sample pre-generated datasets
│   ├── demo_feedback_recent.csv
│   └── demo_feedback_historical.csv
├── scripts/
│   └── generate_feedback.py  # Evolving 4-month synthetic feedback generator
├── services/
│   ├── agent.py              # Query reasoning, recall & evidence synthesis
│   ├── feedback.py           # Ingestion, storage & statistics engine
│   └── llm.py                # Hindsight embedded server & client initialization
└── templates/
    ├── base.html             # Top navbar, Jakarta Sans typography, marked.js
    ├── index.html            # Landing page & architecture showcase
    ├── demo.html             # 4-step guided interactive demo page
    ├── ask.html              # Chat interface with memory citations
    ├── dashboard.html        # Analytics & consolidated observations
    ├── feedback.html         # Single submission form + recent feed
    └── import.html           # File upload + quick-load action cards
```

---

## 👥 HackwithHyderabad 3.0 Submission Info

- **Project:** Vera (User Feedback Intelligence Agent)
- **Memory Engine:** Hindsight (`hindsight-all`) embedded memory bank
- **Evaluation Form:** [Google Form Submission](https://forms.gle/cD7fCnPnkdVm2sH78)
