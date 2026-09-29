from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import json
import logging
from typing import Optional, List, Dict, Any
import io

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import pandas as pd
import markdown

from config import settings, BANK_CONFIG, PRODUCT_AREAS, FEEDBACK_SOURCES
from services.feedback import FeedbackService
from services.agent import AgentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
feedback_service: Optional[FeedbackService] = None
agent_service: Optional[AgentService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - Hindsight embedded server is opt-in (fast local mode by default)"""
    global feedback_service, agent_service

    hindsight_server = None
    client = None

    if settings.HINDSIGHT_URL:
        # Remote Hindsight instance (e.g. Hindsight Cloud)
        from services.llm import get_hindsight_client
        client = get_hindsight_client()
        logger.info(f"Using remote Hindsight at: {settings.HINDSIGHT_URL}")
    elif settings.HINDSIGHT_EMBEDDED:
        from services.llm import get_hindsight_server, get_hindsight_client
        hindsight_server = get_hindsight_server()
        try:
            hindsight_server.__enter__()
            logger.info(f"Hindsight server running at: {hindsight_server.url}")
        except Exception as e:
            logger.warning(f"Hindsight embedded server failed to start: {e}")
            logger.info("Falling back to local mode (no Hindsight server)")
            hindsight_server = None
            # Reset embedded flag so services know we're in local mode
            settings.HINDSIGHT_EMBEDDED = False
        else:
            client = get_hindsight_client()
    else:
        logger.info("Hindsight disabled (local mode) - set HINDSIGHT_URL or HINDSIGHT_EMBEDDED=true to enable")

    if client is not None:
        try:
            await client.acreate_bank(
                bank_id=BANK_CONFIG["bank_id"],
                name=BANK_CONFIG["name"],
                mission=BANK_CONFIG["mission"],
                disposition=BANK_CONFIG["disposition"]
            )
            logger.info(f"Memory bank ready: {BANK_CONFIG['bank_id']}")
        except Exception as e:
            logger.info(f"Memory bank initialization status: {e}")

        # Register bank directives (official SDK: create_directive)
        try:
            existing = await client.alist_directives(bank_id=BANK_CONFIG["bank_id"])
            existing_names = {getattr(d, "name", "") for d in (getattr(existing, "directives", None) or [])}
            for i, directive in enumerate(BANK_CONFIG.get("directives", [])):
                name = f"directive_{i + 1}"
                if name not in existing_names:
                    await client.acreate_directive(
                        bank_id=BANK_CONFIG["bank_id"],
                        name=name,
                        content=directive,
                        priority=10 - i
                    )
            logger.info("Bank directives registered")
        except Exception as e:
            logger.info(f"Directives note: {e}")

    # Initialize services
    feedback_service = FeedbackService(client, BANK_CONFIG["bank_id"])
    agent_service = AgentService(client, BANK_CONFIG["bank_id"], feedback_service=feedback_service)
    
    # Pre-seed with initial baseline feedback (local only, no Hindsight retain to avoid API key issues)
    from scripts.generate_feedback import generate_demo_data
    try:
        initial_data = generate_demo_data(months_back=1)
        # Store locally only for demo UI - Hindsight retain happens on user action
        for item in initial_data[:12]:
            await feedback_service.submit_feedback(
                text=item["text"],
                product_area=item["product_area"],
                source=item["source"],
                user_id=item.get("user_id"),
                date=item.get("date")
            )
        logger.info(f"Pre-seeded with {min(12, len(initial_data))} recent feedback items (local store)")
    except Exception as e:
        logger.warning(f"Pre-seeding note: {e}")

    logger.info("Application startup complete")
    
    yield
    
    # Cleanup
    if hindsight_server is not None:
        try:
            hindsight_server.__exit__(None, None, None)
        except Exception:
            pass
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Vera - Feedback Intelligence Agent",
    description="AI-powered feedback analysis with Hindsight long-term memory",
    version="1.0.0",
    lifespan=lifespan
)

# Static files and templates
static_path = Path("static")
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Pydantic models
class FeedbackInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    product_area: str = Field(default="other")
    source: str = Field(default="in_app_feedback")
    user_id: Optional[str] = None
    date: Optional[str] = None


class FeedbackBatchInput(BaseModel):
    items: List[FeedbackInput]


class QuestionInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    budget: str = Field(default="high")
    types: List[str] = Field(default=["observation", "world", "experience"])


class ImportResponse(BaseModel):
    success: bool
    imported: int
    errors: List[str] = []


# ==========================================
# PAGE ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"active_tab": "home"}
    )


@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="feedback.html",
        context={
            "product_areas": PRODUCT_AREAS,
            "sources": FEEDBACK_SOURCES,
            "active_tab": "feedback"
        }
    )


@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={"active_tab": "import"}
    )


@app.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ask.html",
        context={"active_tab": "ask"}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"active_tab": "dashboard"}
    )


@app.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    stats = await feedback_service.get_stats() if feedback_service else {}
    return templates.TemplateResponse(
        request=request,
        name="demo.html",
        context={
            "active_tab": "demo",
            "stats": stats
        }
    )


# ==========================================
# API ROUTES (Supporting HTMX + JSON)
# ==========================================

@app.post("/api/feedback")
async def submit_feedback(
    request: Request,
    text: Optional[str] = Form(None),
    product_area: Optional[str] = Form("other"),
    source: Optional[str] = Form("in_app_feedback"),
    user_id: Optional[str] = Form(None),
    date: Optional[str] = Form(None)
):
    """Submit a single piece of feedback from Form or JSON"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text", "")
        product_area = body.get("product_area", "other")
        source = body.get("source", "in_app_feedback")
        user_id = body.get("user_id")
        date = body.get("date")

    if not text or len(text.strip()) < 3:
        if "hx-request" in request.headers:
            return HTMLResponse("""
                <div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
                    <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                    <span>Please enter meaningful feedback text (minimum 3 characters).</span>
                </div>
            """)
        raise HTTPException(status_code=400, detail="Feedback text is required")

    result = await feedback_service.submit_feedback(
        text=text,
        product_area=product_area or "other",
        source=source or "in_app_feedback",
        user_id=user_id,
        date=date
    )

    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        area_badge = product_area.replace('_', ' ').title() if product_area else "General"
        src_badge = source.replace('_', ' ').title() if source else "In-App"
        return HTMLResponse(f"""
            <div class="p-5 bg-green-50 border border-green-200 rounded-2xl animate-fade-in">
                <div class="flex items-start gap-3">
                    <div class="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-green-900 text-base">Feedback Retained in Memory Bank!</h4>
                        <p class="text-green-700 text-sm mt-1">Successfully stored in memory bank <code>feedback-intelligence</code> with temporal indexing.</p>
                        <div class="flex flex-wrap items-center gap-2 mt-3 text-xs">
                            <span class="px-2.5 py-1 rounded-md bg-white text-green-800 border border-green-200 font-medium">Doc: {result['document_id']}</span>
                            <span class="px-2.5 py-1 rounded-md bg-white text-gray-700 border border-gray-200">Area: {area_badge}</span>
                            <span class="px-2.5 py-1 rounded-md bg-white text-gray-700 border border-gray-200">Source: {src_badge}</span>
                        </div>
                    </div>
                </div>
            </div>
        """)

    return {"success": True, "result": result}


@app.post("/api/feedback/batch")
async def submit_feedback_batch(batch: FeedbackBatchInput):
    """Submit multiple feedback items"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        results = await feedback_service.submit_feedback_batch(
            items=[item.model_dump() for item in batch.items]
        )
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/recent")
async def get_recent_feedback(request: Request, limit: int = 8):
    """Get recent feedback items formatted for HTMX or JSON"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    items = feedback_service.get_recent(limit=limit)
    
    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        if not items:
            return HTMLResponse("""
                <div class="text-center py-8 text-gray-400">
                    <p>No feedback retained yet. Submit feedback or click "Load Recent" to begin.</p>
                </div>
            """)
        
        cards = []
        for item in items:
            area = item.get("product_area", "other").replace("_", " ").title()
            source = item.get("source", "other").replace("_", " ").title()
            date_str = item.get("date", "")[:10]
            sentiment = item.get("sentiment", "neutral")
            
            sentiment_color = {
                "positive": "bg-green-50 text-green-700 border-green-200",
                "negative": "bg-rose-50 text-rose-700 border-rose-200",
                "neutral": "bg-gray-50 text-gray-700 border-gray-200"
            }.get(sentiment, "bg-gray-50 text-gray-700 border-gray-200")

            cards.append(f"""
                <div class="p-4 bg-white border border-gray-100 hover:border-gray-300 rounded-xl transition shadow-xs flex flex-col justify-between gap-2">
                    <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <div class="flex items-center gap-1.5">
                            <span class="px-2 py-0.5 rounded-full font-medium {sentiment_color} border text-[11px] uppercase tracking-wider">{sentiment}</span>
                            <span class="font-medium text-gray-800">{area}</span>
                        </div>
                        <span>{date_str}</span>
                    </div>
                    <p class="text-sm text-gray-800 leading-relaxed font-normal">"{item.get('text', '')}"</p>
                    <div class="flex items-center justify-between text-[11px] text-gray-400 pt-2 border-t border-gray-50">
                        <span>Via: {source}</span>
                        <span>User: {item.get('user_id', 'anonymous')}</span>
                    </div>
                </div>
            """)
        return HTMLResponse(f"""
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 animate-fade-in">
                {''.join(cards)}
            </div>
        """)

    return {"items": items}


@app.post("/api/import")
async def import_feedback(request: Request, file: UploadFile = File(...)):
    """Import feedback from CSV or JSON"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith('.json'):
            df = pd.read_json(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or JSON.")
        
        if 'text' not in df.columns:
            raise HTTPException(status_code=400, detail="Missing required column: 'text'")
        
        items = []
        for _, row in df.iterrows():
            item = {
                "text": str(row.get('text', '')),
                "product_area": str(row.get('product_area', 'other')),
                "source": str(row.get('source', 'in_app_feedback')),
                "user_id": str(row.get('user_id', '')) if pd.notna(row.get('user_id')) else None,
                "date": str(row.get('date', '')) if pd.notna(row.get('date')) else None,
            }
            items.append(item)
        
        results = await feedback_service.submit_feedback_batch(items=items)
        
        if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(f"""
                <div class="p-6 bg-purple-50 border border-purple-200 rounded-2xl animate-fade-in">
                    <div class="flex items-start gap-4">
                        <div class="w-10 h-10 rounded-xl bg-purple-600 text-white flex items-center justify-center flex-shrink-0">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        </div>
                        <div>
                            <h4 class="font-bold text-purple-900 text-lg">Dataset Successfully Imported!</h4>
                            <p class="text-purple-700 text-sm mt-1">Processed <strong>{len(results)} items</strong> from <code>{file.filename}</code> into Hindsight memory bank.</p>
                            <div class="mt-4 flex gap-3">
                                <a href="/ask" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg transition inline-flex items-center gap-1.5 shadow-sm">
                                    <span>Ask the Agent</span>
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                                </a>
                                <a href="/dashboard" class="px-4 py-2 bg-white text-purple-700 border border-purple-200 hover:bg-purple-50 text-sm font-semibold rounded-lg transition">
                                    View Dashboard
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            """)

        return ImportResponse(
            success=True,
            imported=len(results),
            errors=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        if "hx-request" in request.headers:
            return HTMLResponse(f"""
                <div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                    <strong>Import Error:</strong> {str(e)}
                </div>
            """)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history")
async def get_chat_history():
    """Return welcoming starter chat state"""
    return HTMLResponse("""
        <div class="space-y-4">
            <div class="flex items-start gap-3">
                <div class="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.734-.988-2.386l-.548-.547z"></path></svg>
                </div>
                <div class="bg-white border border-gray-200 rounded-2xl p-4 shadow-xs max-w-2xl text-gray-800">
                    <p class="font-medium text-gray-900 mb-1">Hello! I am Vera, your Feedback Intelligence Agent.</p>
                    <p class="text-sm text-gray-600 leading-relaxed">
                        I remember all customer feedback across time. Ask me about recurring complaints, sentiment trajectories, or specific features like <strong>PDF upload</strong> or <strong>login</strong>!
                    </p>
                </div>
            </div>
        </div>
    """)


@app.post("/api/ask")
async def ask_agent(
    request: Request,
    question: Optional[str] = Form(None),
    budget: Optional[str] = Form("high"),
    mode: Optional[str] = Form("recall")
):
    """Ask the agent a question - supports HTMX form or JSON API with recall vs reflect modes"""
    if not agent_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        question = body.get("question", "")
        budget = body.get("budget", "high")
        mode = body.get("mode", "recall")

    if not question:
        if "hx-request" in request.headers:
            return HTMLResponse("""
                <div class="p-3 bg-amber-50 text-amber-800 text-sm rounded-xl">Please ask a question.</div>
            """)
        raise HTTPException(status_code=400, detail="Question is required")

    force_reflect = (mode == "reflect")
    result = await agent_service.ask(
        question=question,
        budget=budget or "high",
        force_reflect=force_reflect
    )

    rendered_answer = markdown.markdown(
        result["answer"],
        extensions=["tables", "fenced_code", "nl2br"]
    )

    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        evidence_items = result.get("evidence", [])
        evidence_badges = []
        for ev in evidence_items[:6]:
            date_short = ev.get("date", "")[:10]
            area_badge = ev.get("product_area", "").replace("_", " ").title()
            evidence_badges.append(f"""
                <div class="p-2.5 bg-gray-50 border border-gray-200 rounded-lg text-xs space-y-1">
                    <div class="flex items-center justify-between text-gray-500 font-medium">
                        <span class="text-blue-600">{area_badge}</span>
                        <span>{date_short}</span>
                    </div>
                    <p class="text-gray-700 italic font-normal">"{ev.get('text', '')}"</p>
                </div>
            """)

        evidence_section = ""
        if evidence_badges:
            evidence_section = f"""
                <div class="mt-4 pt-4 border-t border-gray-100">
                    <details class="text-xs">
                        <summary class="font-semibold text-gray-600 cursor-pointer hover:text-blue-600 flex items-center gap-1.5">
                            <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                            <span>Recalled Evidence ({len(evidence_items)} Memories Cited)</span>
                        </summary>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2.5">
                            {''.join(evidence_badges)}
                        </div>
                    </details>
                </div>
            """

        mode_badge = ""
        if result.get("mode") == "hindsight_reflect" or mode == "reflect":
            mode_badge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-purple-100 text-purple-800 font-bold border border-purple-200">⚡ Hindsight areflect() Deep Analysis</span>'
        elif result.get("mode") == "live_openai":
            mode_badge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-green-100 text-green-800 font-medium">● GPT-4o-mini Live</span>'
        elif result.get("hindsight_recalled"):
            mode_badge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-blue-100 text-blue-800 font-medium">● Hindsight RECALL + TEMPR</span>'
        else:
            mode_badge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-gray-100 text-gray-700 font-medium">● Local Memory Mode</span>'

        return HTMLResponse(f"""
            <!-- User Question Bubble -->
            <div class="flex items-start justify-end gap-3 animate-fade-in">
                <div class="bg-blue-600 text-white rounded-2xl rounded-tr-none px-4 py-3 max-w-2xl shadow-sm text-sm font-medium">
                    {question}
                </div>
                <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                    You
                </div>
            </div>

            <!-- Agent Response Bubble -->
            <div class="flex items-start gap-3 animate-fade-in">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.734-.988-2.386l-.548-.547z"></path></svg>
                </div>
                <div class="bg-white border border-gray-200 rounded-2xl rounded-tl-none p-5 shadow-xs max-w-3xl text-gray-800 w-full">
                    <div class="flex items-center justify-between pb-3 mb-3 border-b border-gray-100 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="font-bold text-gray-900">Vera (Feedback Intelligence Agent)</span>
                            {mode_badge}
                        </div>
                        <span class="text-gray-400">{datetime.now().strftime('%H:%M')}</span>
                    </div>

                    <div class="prose prose-sm max-w-none text-gray-800 leading-relaxed">
                        {rendered_answer}
                    </div>

                    {evidence_section}
                </div>
            </div>
        """)

    return result


@app.get("/api/stats")
async def get_stats(request: Request):
    """Get basic statistics about stored feedback"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    stats = await feedback_service.get_stats()
    
    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        total = stats.get("total_memories", 0)
        top_area = stats.get("top_product_area", "None").replace("_", " ").title()
        top_count = stats.get("top_product_area_count", 0)
        neg_pct = stats.get("sentiment_percentages", {}).get("negative", 0)
        pos_pct = stats.get("sentiment_percentages", {}).get("positive", 0)

        return HTMLResponse(f"""
            <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-xs flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                </div>
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Memories</p>
                    <h3 class="text-2xl font-bold text-gray-900 mt-0.5">{total}</h3>
                    <p class="text-[11px] text-green-600 font-medium mt-0.5">● Hindsight Bank Active</p>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-xs flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center flex-shrink-0">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase tracking-wider">Top Issue Area</p>
                    <h3 class="text-2xl font-bold text-gray-900 mt-0.5">{top_area}</h3>
                    <p class="text-[11px] text-rose-600 font-medium mt-0.5">{top_count} total mentions</p>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-xs flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path></svg>
                </div>
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase tracking-wider">Negative Sentiment</p>
                    <h3 class="text-2xl font-bold text-gray-900 mt-0.5">{neg_pct}%</h3>
                    <p class="text-[11px] text-gray-500 font-medium mt-0.5">High severity issues</p>
                </div>
            </div>

            <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-xs flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                </div>
                <div>
                    <p class="text-xs font-medium text-gray-500 uppercase tracking-wider">Positive Sentiment</p>
                    <h3 class="text-2xl font-bold text-gray-900 mt-0.5">{pos_pct}%</h3>
                    <p class="text-[11px] text-emerald-600 font-medium mt-0.5">SSO & UX improvements</p>
                </div>
            </div>
        """)

    return stats


@app.get("/api/trends")
async def get_trends(request: Request):
    """Get trend analysis from the agent"""
    if not agent_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    trends = await agent_service.get_trends()
    
    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        rendered_trends = markdown.markdown(
            trends["trends_analysis"],
            extensions=["tables", "fenced_code", "nl2br"]
        )

        obs_cards = []
        for obs in trends.get("raw_observations", []):
            obs_cards.append(f"""
                <div class="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2">
                    <div class="flex items-center justify-between text-xs text-gray-500 font-medium">
                        <span class="text-purple-600 font-semibold">Observation</span>
                        <span>{obs.get('date', '2025-04')}</span>
                    </div>
                    <p class="text-sm font-medium text-gray-800 leading-snug">{obs.get('text')}</p>
                    <p class="text-xs text-gray-500">Supported by {obs.get('source_fact_count', 0)} source facts</p>
                </div>
            """)

        return HTMLResponse(f"""
            <div class="space-y-6 animate-fade-in">
                <div class="prose max-w-none text-gray-800">
                    {rendered_trends}
                </div>

                <div class="mt-8 pt-6 border-t border-gray-100">
                    <h4 class="font-bold text-gray-900 text-sm mb-3">Consolidated Hindsight Observations</h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {''.join(obs_cards)}
                    </div>
                </div>
            </div>
        """)

    return trends


@app.post("/api/demo/load-recent")
async def load_recent_feedback(request: Request):
    """Load only recent feedback (last month) for demo step 1"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        from scripts.generate_feedback import generate_demo_data
        recent_data = generate_demo_data(months_back=1)
        results = await feedback_service.submit_feedback_batch(items=recent_data)
        
        if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(f"""
                <div class="p-5 bg-blue-50 border border-blue-200 rounded-2xl animate-fade-in">
                    <div class="flex items-start gap-3">
                        <div class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        </div>
                        <div>
                            <h4 class="font-bold text-blue-900 text-base">Loaded Recent Feedback (1 Month)</h4>
                            <p class="text-blue-700 text-sm mt-0.5">Successfully retained <strong>{len(results)} items</strong> (April 2025 data only) into Hindsight.</p>
                            <p class="text-xs text-blue-600 mt-2 font-medium">➡️ Next Step: Go to Demo Flow Step 2 to query recent memory.</p>
                        </div>
                    </div>
                </div>
            """)

        return {"success": True, "loaded": len(results), "period": "last month"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/demo/load-historical")
async def load_historical_feedback(request: Request):
    """Load full historical feedback for demo step 3"""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        from scripts.generate_feedback import generate_demo_data
        historical_data = generate_demo_data(months_back=4)
        results = await feedback_service.submit_feedback_batch(items=historical_data)
        
        if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(f"""
                <div class="p-5 bg-purple-50 border border-purple-200 rounded-2xl animate-fade-in">
                    <div class="flex items-start gap-3">
                        <div class="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center flex-shrink-0">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        </div>
                        <div>
                            <h4 class="font-bold text-purple-900 text-base">Loaded Full Historical Dataset (4 Months)</h4>
                            <p class="text-purple-700 text-sm mt-0.5">Retained <strong>{len(results)} items</strong> spanning Jan, Feb, Mar, and Apr 2025.</p>
                            <p class="text-xs text-purple-600 mt-2 font-medium">🎉 Memory Bank Expanded! Observations and cross-month timelines consolidated.</p>
                        </div>
                    </div>
                </div>
            """)

        return {"success": True, "loaded": len(results), "period": "last 4 months"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/demo/reset")
async def reset_demo(request: Request):
    """Reset the demo state for a clean run"""
    if feedback_service:
        feedback_service.clear()
        try:
            await feedback_service.clear_bank()
        except Exception:
            pass
    
    if "hx-request" in request.headers or "text/html" in request.headers.get("accept", ""):
        return HTMLResponse("""
            <div class="p-4 bg-gray-100 border border-gray-200 rounded-xl text-gray-700 text-sm font-medium">
                Demo state reset. Memory is fresh and ready for Step 1.
            </div>
        """)
    return {"success": True, "message": "Demo memory reset"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", settings.PORT or settings.APP_PORT))
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=port,
        reload=settings.DEBUG
    )