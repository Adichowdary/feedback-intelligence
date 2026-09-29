# Vera: Giving User Feedback a Memory

> *Built for HackwithHyderabad 3.0 • Track: Agentic Memory & Reasoning • Powered by Hindsight*

---

## The Problem

Product teams receive user feedback from everywhere: customer support tickets (Zendesk), in-app rating widgets, App Store reviews, community Discord channels, and imported CSV datasets.

The problem isn't simply collecting feedback. **It is understanding how that feedback changes over time.**

A complaint that appears today as a critical outage may have appeared three months ago as a subtle, neglected latency issue. A product update might alter how users express frustration without solving the root cause—or it might successfully fix a problem, yet team leaders lack the historical visibility to confirm that complaints actually ceased.

Traditional LLM agents suffer from fundamental amnesia. When you ask a stateless agent:

> *"What's broken with our app right now?"*

it only sees whatever text happens to be crammed into its immediate prompt window. It has no baseline, cannot calculate temporal trajectories, and cannot determine whether an issue is a sudden regression from yesterday's deploy or a chronic architectural bottleneck.

We wanted to build something that could connect those pieces across weeks and months.

That led us to **Vera**, an **AI Feedback Intelligence Agent** designed to retain every piece of customer feedback into long-term memory and leverage that historical timeline when answering strategic product questions.

---

## What Vera Does

Vera allows product managers and engineering leads to submit individual feedback in real-time, import historical CSV/JSON datasets, and query feedback trends using natural language.

Instead of treating every inquiry independently or relying on rigid vector-similarity search, Vera uses **Hindsight** (`hindsight-all`) as its dedicated long-term memory layer.

### The Core Information Flow

```
User Feedback (Support Tickets, In-App Reviews, CSVs)
                       ↓
         FastAPI Backend Ingestion Layer
                       ↓
               Hindsight RETAIN
                       ↓
   Long-Term Memory Bank (Entity Graphs & Chronology)
                       ↓
       Product Manager / Engineer Query
                       ↓
        Hindsight RECALL / areflect()
                       ↓
 Relevant Multi-Month Context & Verbatim Evidence
                       ↓
       Temporal Reasoning & Synthesis
                       ↓
 Strategic Product Insight & Root Cause Action Plan
```

The guiding principle of Vera is straightforward:

> **The more feedback Vera remembers, the more useful its historical understanding becomes.**

---

## Why We Chose Memory

A conventional LLM can summarize whatever information is provided in the prompt. For example:

> *"What are the biggest complaints in this 50-row CSV?"*

A basic prompt can easily count occurrences of words like "slow" or "login error." But questions that drive strategic engineering decisions require longitudinal context:

> *"How has the PDF upload problem changed over the last four months?"*  
> *"Did our March deployment introduce new bugs or worsen existing ones?"*  
> *"Did launching SAML SSO in April actually resolve customer login frustration?"*

Without long-term memory, answering these requires engineers to write complex custom SQL queries, extract timestamped sentiment trends, and manually piece together the timeline.

This is where **Hindsight** became central to our design. Instead of a naive pipeline:

Feedback → LLM → Answer

Vera implements an agentic memory loop:

Feedback → RETAIN → Memory Bank
                         ↓
Question → RECALL / REFLECT → Chronological Context → LLM Reasoning → Actionable Insight

### Why This Architecture Mattered

1. **Elimination of Context Window Limits:** Rather than stuffing thousands of user reviews into a token-limited context window, Hindsight retains observations over time and consolidates them into an associative memory graph.
2. **Temporal Grounding (TEMPR):** Hindsight indexes memories not merely by semantic similarity, but by when events actually occurred (`timestamp`, `occurred_start`, `mentioned_at`). This enables genuine chronological reasoning.
3. **Verbatim Traceability:** Every conclusion Vera draws is backed by verifiable citations (exact date, user ID, channel source, and verbatim text), completely eliminating hallucinated claims.

---

## How Vera Uses Hindsight

When feedback enters Vera—whether through the live feedback submission widget, batch CSV upload, or synthetic historical backfill—it passes through the `FeedbackService` layer. 

We invoke Hindsight's `aretain()` operation to store the content alongside structured metadata, product area categorization, and UTC timestamps.

Later, when a user asks a question, Vera's `AgentService` inspects the inquiry. For simple factual lookups, it invokes `arecall()`. For questions involving evolution, root causes, or before-and-after comparisons, Vera invokes Hindsight's deep `areflect()` engine.

### 1. Retaining User Feedback (Real Implementation)

Here is the exact asynchronous retention method from `services/feedback.py`:

```python
async def submit_feedback(
    self,
    text: str,
    product_area: str = "other",
    source: str = "in_app_feedback",
    user_id: Optional[str] = None,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """Submit a single feedback item to Hindsight with seamless fallback"""
    timestamp = self._parse_date(date)
    date_str = timestamp.isoformat()
    document_id = f"feedback_{uuid.uuid4().hex[:12]}"
    
    metadata = {
        "product_area": product_area,
        "source": source,
    }
    if user_id:
        metadata["user_id"] = user_id
    
    tags = [
        "feedback",
        f"product_area:{product_area}",
        f"source:{source}"
    ]
    if user_id:
        tags.append(f"user:{user_id}")
    context = f"user_feedback_{product_area}_{source}"

    # Retain into Hindsight Long-Term Memory Bank
    result = await self.client.aretain(
        bank_id=self.bank_id,
        content=text,
        context=context,
        timestamp=date_str,
        document_id=document_id,
        metadata=metadata,
        tags=tags
    )
    return {"document_id": document_id, "success": True, "date": date_str}
```

#### What Is Being Retained:
- **`content`:** The verbatim user complaint, review, or ticket message.
- **`timestamp`:** Normalized ISO-8601 UTC timestamp preserving when the customer reported the issue.
- **`tags` & `metadata`:** Facets identifying the `product_area` (`pdf_upload`, `login`, `billing`, etc.) and the customer touchpoint (`support_ticket`, `in_app_feedback`, `app_store`).
- **`bank_id`:** The isolated memory namespace (`feedback-intelligence`).

---

### 2. Retrieving Context with Recall & Reflect (Real Implementation)

Here is the exact retrieval and reasoning flow from `services/agent.py`:

```python
async def ask(
    self,
    question: str,
    budget: str = "high",
    types: List[str] = None,
    force_reflect: bool = False
) -> Dict[str, Any]:
    """Query Vera using Hindsight recall/reflect + LLM temporal reasoning"""
    if types is None:
        types = ["observation", "world", "experience"]

    use_reflect = force_reflect or self._should_use_reflect(question)

    # 1. Deep Analysis: Trigger Hindsight areflect() for temporal questions
    if use_reflect:
        reflect_response = await self.client.areflect(
            bank_id=self.bank_id,
            query=question,
            budget=budget,
            max_tokens=4096,
        )
        if hasattr(reflect_response, "text") and reflect_response.text:
            return {"answer": reflect_response.text, "mode": "hindsight_reflect"}

    # 2. Standard Recall: Multi-strategy TEMPR memory recall
    recall_response = await self.client.arecall(
        bank_id=self.bank_id,
        query=question,
        types=types,
        budget=budget,
        max_tokens=4096,
        prefer_observations=True
    )
    
    evidence = []
    for memory in recall_response.results:
        evidence.append({
            "id": getattr(memory, "id", "mem_1"),
            "text": getattr(memory, "text", ""),
            "date": getattr(memory, "occurred_start", None) or "2025-04",
            "type": getattr(memory, "type", "observation"),
        })

    # 3. Synthesize evidence into actionable executive recommendations
    return await self._synthesize_response(question, evidence)
```

#### How Retrieval Works:
- **Query Classification:** Questions containing temporal cues (*"how has"*, *"changed over time"*, *"before vs after"*) automatically route to `areflect()`.
- **Observation Prioritization:** Setting `prefer_observations=True` directs Hindsight to retrieve synthesized behavioral patterns rather than raw, fragmented sentences.
- **Evidence Extraction:** Retrieved memory nodes provide exact dates and text snippets directly cited in Vera's output.

---

### Official Resources Used
- **Hindsight Repository:** [https://github.com/vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)
- **Hindsight Documentation:** [https://docs.hindsight.vectorize.io](https://docs.hindsight.vectorize.io)
- **Vectorize Agent Memory Guides:** [https://vectorize.io](https://vectorize.io)

---

## The Kind of Questions Vera Can Answer

Because Vera indexes feedback along a continuous temporal axis, it excels at inquiries that require longitudinal understanding:

1. **Root-Cause Evolution:** *"How has the PDF upload problem changed over time?"*
2. **Before-and-After Analysis:** *"What did users say about login before and after SSO was introduced?"*
3. **Emerging Friction:** *"Are there any new issues that started appearing in March that we didn't see in January?"*
4. **Resolution Validation:** *"Did customer complaints regarding invoice downloads drop after our February patch?"*
5. **Sentiment & Channel Drift:** *"Which product areas receive the highest concentration of negative tickets from enterprise users?"*
6. **Cross-Module Correlations:** *"How do dashboard loading complaints correlate with database export timeouts?"*

---

## The Before-and-After Moment

This contrast is the centerpiece of Vera's interactive demo (`/demo`) and clearly illustrates why memory matters.

### 🔴 BEFORE: The Stateless Baseline (Recent Data Only)

In Step 1 of the demo, we establish the baseline by only ingesting recent feedback from April 2025 (~60 items). The agent has no historical memory of earlier months.

We ask Vera:

> **User:** *"What are the main problems users are experiencing right now?"*

**Vera Responds:**
```markdown
### 📊 Executive Summary
Based on recent user feedback from April 2025, the primary operational issue is
failure in PDF document uploads. Users report repeated 504 Gateway Timeout errors
and dropped connections.

Key Findings:
• PDF uploads are failing with near 100% failure rate for files above 5MB.
• Evidence: "PDF upload keeps failing with timeout errors after the latest update" (Support Ticket, 2025-04)

Diagnosis:
This appears to be a sudden, isolated regression likely caused by the most recent patch.
Recommended Action: Inspect recent pull requests touching the upload handler.
```

**The Flaw:**  
The diagnosis is superficially accurate for April, but **completely wrong on root cause**. It assumes the issue is a brand-new bug introduced yesterday. It has no idea that users have been warning about this for four months.

---

### 🟢 AFTER: Long-Term Memory Activated (4 Months of History)

In Step 3 of the demo, we ingest the full historical dataset (January through April 2025, expanding the memory bank to 285+ records).

We ask Vera the temporal question:

> **User:** *"How has the PDF upload problem changed over time?"*

**Vera Responds with Full Temporal Synthesis:**
```markdown
### 📊 Chronological Evolution Analysis: PDF Upload

Based on 285 historical memories tracked from January to April 2025, the PDF Upload
module has experienced a severe and progressive functional degradation across four stages:

1. January 2025 (Initial Latency / Warning Signs):
   Users reported early friction where uploads took 30+ seconds on large attachments.
   • Evidence: "PDF upload takes over 30 seconds for 10-page contracts" (Feedback, 2025-01-18)

2. February 2025 (Unresolved Degradation):
   Complaints grew as users frequently encountered stalled progress bars during peak hours.
   No engineering intervention was deployed.

3. March 2025 (The Turning Point / Breaking Change):
   A major deployment updated the networking proxy and payload limits. This converted 
   the pre-existing latency into fatal connection resets and 504 Gateway Timeouts.
   • Evidence: "PDF upload keeps failing with timeout errors after the March update" (Ticket, 2025-03-12)

4. April 2025 (Critical Blocker / Current State):
   The failure rate reached near 100%, completely blocking customer billing workflows.

Key Strategic Insight:
Without historical memory, an agent only observing April data diagnoses a "new sudden bug."
Hindsight reveals that this was an unmonitored 4-month infrastructure bottleneck that
collapsed under payload limits during the March release.

Resolved Areas Surfaced:
Interestingly, customer complaints regarding Login dropped by 92% in April following
the deployment of SAML SSO, confirming that authentication pain was successfully resolved.
```

### What Vera Understood That Stateless Agents Missed:
1. **The Bug Wasn't New:** It had been brewing since January as a silent latency issue.
2. **The Catalyst:** The March deploy didn't create the problem; it tightened timeout thresholds, exposing existing technical debt.
3. **Product Wins:** Vera verified that while PDF uploads worsened, Login issues were simultaneously cured by the SSO rollout.

---

## A Real Example from the Dataset

Below is the concrete data trajectory from our synthetic 4-month dataset (`data/demo_feedback_historical.csv`):

| Month | Verbatim User Feedback | Product Area | Channel | Vera's Memory Classification |
|---|---|---|---|---|
| **Jan 2025** | *"PDF invoice export takes almost 40 seconds to process. Please speed this up."* | `pdf_upload` | In-App Feedback | Warning Sign (Latency) |
| **Feb 2025** | *"The upload spinner keeps spinning forever when uploading scanned receipts."* | `pdf_upload` | Support Ticket | Chronic Friction |
| **Mar 2025** | *"Ever since the v2.4 release on March 10th, uploads fail with 504 Gateway Timeouts."* | `pdf_upload` | Support Ticket | **Breaking Regression** |
| **Apr 2025** | *"URGENT: Entire accounting team cannot attach PDFs. Upload fails immediately."* | `pdf_upload` | Zendesk Escalation | **Critical Blocker** |
| **Apr 2025** | *"Single Sign-On with Okta works flawlessly now. So glad password resets are gone!"* | `login` | App Review | **Positive Resolution** |

Vera automatically clusters these data points across months into a cohesive narrative, providing engineering leadership with both root-cause diagnostics and release impact verification.

---

## How We Kept the Interface Simple

We designed Vera as an interaction layer around an intelligent agent, rather than an overwhelming analytics dashboard with dozens of confusing sub-menus.

The interface centers on four streamlined workflows:

1. **Interactive Demo Flow (`/demo`):** A guided 4-step walkthrough with an animated **Chart.js Memory Growth Tracker** that shows the memory bank expanding from ~60 to 285+ records in real time, accompanied by a 4-stage visual timeline and a Before/After comparison card.
2. **Conversational Agent (`/ask`):** A natural chat UI equipped with suggestion chips, direct memory citation badges, and an **"Ask with Reflect"** button for deep historical synthesis.
3. **Executive Dashboard (`/dashboard`):** Real-time sentiment distribution, top product area breakdown, and automated trend synthesis cards powered by HTMX polling.
4. **Data Ingestion (`/import` & `/feedback`):** Single-item feedback capture with instant tagging and drag-and-drop CSV batch ingestion.

### Architectural Stack
- **Backend:** FastAPI (Python 3.10+) with asynchronous lifespan management.
- **Frontend:** Jinja2 templates styled with Tailwind CSS, micro-interactions with Alpine.js, and seamless server-driven updates via HTMX.
- **Visualization:** Responsive HTML5 Canvas with Chart.js 4.4.1.
- **Dual-Mode Resilience:** Seamless fallback architecture that operates locally offline using built-in TEMPR evidence synthesis, or connects directly to Hindsight Cloud (`api.hindsight.vectorize.io`).

---

## What We Learned

### 1. Memory Must Be a First-Class Architecture, Not a Feature
Adding "memory" by simply appending previous chat messages into the prompt quickly saturates the context window and dilutes the model's focus. True agentic memory requires an external, structured memory bank that indexes, generalizes, and extracts entities across independent ingestion cycles.

### 2. Temporal Grounding Completely Changes Agent Utility
Most RAG systems prioritize semantic similarity ("find documents that contain words similar to this query"). But for customer feedback, **when** something happened is often far more important than **how similar** the words are. Hindsight's temporal indexing provided the chronological anchors Vera needed to distinguish between resolved past issues and escalating current problems.

### 3. Citations Are Essential for Trust in AI Analytics
Product managers will not make roadmap decisions based on vague AI assertions like *"Users seem unhappy with PDF uploads."* When Vera provides verbatim quotes with dates, ticket IDs, and channel sources, it gives leadership the confidence to prioritize engineering tickets.

### 4. Build for Resilience and Graceful Fallback
Network latency and third-party API rate limits are inevitable in live hackathon presentations. Designing Vera with a dual-mode fallback architecture—allowing offline local operation alongside full cloud connectivity—guaranteed 100% demo reliability without sacrificing deep agentic behavior.

### 5. Agents Should Surface Unintended Wins Alongside Failures
When evaluating product health, teams often fixate exclusively on what is broken. A pleasant surprise during development was seeing Vera recognize that while PDF uploads were failing, login complaints had completely vanished after the SSO launch. An intelligent agent should confirm successes as well as surface failures.

---

## What We Would Improve

While the core `RETAIN → RECALL → REASON → INSIGHT` loop is fully operational, future iterations could include:

1. **Automated Proactive Alerting:** Configuring background cron jobs within Vera to monitor memory banks and push Slack or Linear alerts whenever an issue transitions from "latency friction" to "breaking regression."
2. **Multi-Tenant Team Partitioning:** Supporting organization-level memory banks where different teams (Growth, Infrastructure, Security) have dedicated memory scopes with cross-bank federated queries.
3. **Native Issue Tracker Bi-directional Sync:** Enabling Vera to automatically create GitHub Issues or Jira tickets with cited feedback evidence when a P0 blocker is detected.
4. **Voice-Driven Executive Briefings:** Integrating text-to-speech to deliver 60-second weekly executive audio briefs summarizing feedback sentiment shifts.

---

## Final Thoughts

Vera started with a simple observation: **User feedback becomes exponentially more valuable when an agent remembers its evolution.**

Instead of treating customer complaints as disposable, isolated tickets, Vera links feedback across time to tell the complete product story. By combining FastAPI, HTMX, and Hindsight's long-term memory engine, we transformed an AI agent from a basic query bot into a strategic feedback analyst that understands cause, effect, and time.

---

## Visuals & Submission Artifacts

- **Screenshot 1 (Main UI):** The Vera landing page showing the architectural memory loop.
- **Screenshot 2 (Ingestion):** Drag-and-drop CSV batch import at `/import` and live submission feed at `/feedback`.
- **Screenshot 3 (Memory Bank Growth):** Chart.js animated memory graph at `/demo` scaling from ~60 to 285+ verified observations.
- **Screenshot 4 (Aha! Moment & Timeline):** The 4-stage visual chronological timeline and Before/After comparison at Step 4.
- **Screenshot 5 (Ask with Reflect):** Conversational chat at `/ask` with purple `areflect()` deep analysis badge and verbatim citations.
- **Live Demo URL:** `http://localhost:8000/demo`
- **Submission Link:** [Google Form Submission](https://forms.gle/cD7fCnPnkdVm2sH78)
- **Built for:** HackwithHyderabad 3.0 (Track: Agentic Memory & Reasoning)
