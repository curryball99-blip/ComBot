"""
LangGraph FastAPI Application
============================

FastAPI application that integrates the LangGraph dual document processing workflow
with frontend connectivity and JIRA dashboard functionality.

Semantic Retrieval Behavior (Added v3):
--------------------------------------
1. Primary path: exact ticket key detection -> scroll filtered chunks (latest ingestion_version only).
2. Fallback path: if no ticket key context assembled, perform semantic vector search over enriched JIRA chunks.
3. Both paths apply guardrails based on resolved vs active ticket distribution.
4. Debug of final assembled prompt/context available at /api/debug/last_prompt.
5. Assist endpoint /api/jira/assist/{ticket_key} supplies targeted guidance for unresolved tickets leveraging resolved references.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import uuid
from datetime import datetime
import logging
from typing import Optional, List, Dict, Any
from .prompt_templates import (
    system_prompt_analysis,
    system_prompt_prioritized_troubleshoot,
    build_user_prompt_analysis,
    build_user_prompt_prioritized_troubleshoot,
    SOLUTION_SCHEMA_BRIEF,
    SOLUTION_SCHEMA_START_WITH,
)
import os
from dotenv import load_dotenv, find_dotenv

# LangGraph imports (relative)
from .langgraph_workflow import DualDocumentProcessingWorkflow
from .langgraph_state_schema import DocumentProcessingState
from .embedding_service_factory import create_embedding_backend
from .jira_qdrant_service import JiraQdrantService
from .ticket_reranker_service import ticket_reranker_service
from .groq_client_async import AsyncGroqClient
from .chat_context_service import ChatContextService
import re, httpx

# JIRA / services imports (relative)
from .jira_service import JiraService
from .jira_dashboard import JiraDashboard
from .team_analytics_service import TeamAnalyticsService
from .resolution_assist_service import ResolutionAssistService
from .ticket_data_extractor import ticket_data_extractor

# (Defer .env load until after logger is defined)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from repository root or current dir (after logger available)
_env_path = find_dotenv(usecwd=True) or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path, override=True)
    logger.info(f"🔑 Loaded environment variables from {_env_path}")
else:
    logger.warning("⚠️ Could not locate .env file for environment variable loading")

app = FastAPI(
    title="LangGraph RAG Chatbot",
    description="Advanced RAG chatbot with LangGraph workflow orchestration",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://172.25.39.78:3000",  # previous internal IP
        "http://3.7.91.225:3000",    # public IP dev server
        "http://3.7.91.225",         # optional if served on port 80 later
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = True
    internet_search: bool = False
    # AI Parameters
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    top_p: Optional[float] = 0.9
    # Use environment default if provided, fallback to current recommended model
    model: Optional[str] = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    custom_system_prompt: Optional[str] = None
    use_custom_prompt: Optional[bool] = False
    # Performance / behavior toggles
    fast: Optional[bool] = False  # skip semantic fallback when True
    legacy_mode: Optional[bool] = False  # use earlier simpler semantic formatting for stable answers

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    session_id: str
    timestamp: str

class SearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None
    limit: Optional[int] = 10
    score_threshold: Optional[float] = 0.7

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    total_results: int
    processing_time: float

class DocumentUploadResponse(BaseModel):
    message: str
    filename: str
    file_id: str
    chunks_created: int
    vectors_stored: int

# JIRA Models
class JiraTicketRequest(BaseModel):
    project_key: str
    summary: str
    description: str
    issue_type: str = 'Task'

class JiraCommentRequest(BaseModel):
    ticket_key: str
    comment: str

class JiraAssistResponse(BaseModel):
    ticket_key: str
    status: str
    resolved_reference_count: int
    references: List[Dict[str, Any]]
    suggestion: str

# JIRA Analysis Models
class JiraAnalyzeRequest(BaseModel):
    ticket_key: str
    max_references: Optional[int] = 5
    include_semantic_search: Optional[bool] = True
    analysis_depth: Optional[str] = "comprehensive"  # "quick", "standard", "comprehensive"

class JiraAnalyzeResponse(BaseModel):
    ticket_key: str
    status: str
    is_resolved: bool
    analysis_type: str  # "resolved_summary", "unresolved_analysis"
    resolved_reference_count: int
    references: List[Dict[str, Any]]
    ai_analysis: str
    troubleshooting_steps: List[str]
    confidence_score: float
    retrieval_method: str  # "semantic", "lexical", "fallback"
    processing_time: float
    timestamp: str

@app.get("/api/debug/last_prompt")
async def debug_last_prompt():
    if not _LAST_PROMPT_DEBUG:
        return {"status": "empty"}
    # Redact overly long context for transport if needed
    data = dict(_LAST_PROMPT_DEBUG)
    if len(data.get('final_context','')) > 15000:
        data['final_context'] = data['final_context'][:15000] + '... [TRUNCATED]'
    return data

@app.get("/api/debug/embedding")
async def debug_embedding_backend():
    """Return current embedding backend diagnostics (model, dimension, batch size if available)."""
    emb = services.get('embedding')
    if not emb:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    def safe(getter, default=None):
        try:
            return getter()
        except Exception as e:
            return f"error: {e}" if default is None else default
    model_name = safe(lambda: getattr(emb,'model_name','unknown'))
    device = safe(lambda: str(getattr(emb,'_device', 'unknown')))
    batch_size = safe(lambda: getattr(emb,'_batch_size', None))
    dimension = safe(lambda: emb.get_dimension() if hasattr(emb,'get_dimension') else None)
    return {
        "ok": True,
        "model": model_name,
        "device": device,
        "batch_size": batch_size,
        "dimension": dimension,
        "class": emb.__class__.__name__,
    }

@app.get("/api/debug/embedding2")
async def debug_embedding_backend_minimal():
    """Minimal diagnostic endpoint to verify embedding service presence and basic attributes."""
    try:
        emb = services.get('embedding')
    except Exception as e:
        return {"ok": False, "error": f"services access error: {e}"}
    if not emb:
        return {"ok": False, "error": "embedding service missing"}
    resp = {"ok": True}
    for attr in ["model_name", "_device", "_batch_size"]:
        try:
            v = getattr(emb, attr, None)
            resp[attr.replace('_','')] = str(v)
        except Exception as e:
            resp[attr.replace('_','')+"_error"] = str(e)
    try:
        resp['dimension'] = emb.get_dimension() if hasattr(emb,'get_dimension') else None
    except Exception as e:
        resp['dimension_error'] = str(e)
    resp['class'] = emb.__class__.__name__
    return resp

class JiraSearchRequest(BaseModel):
    query: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    max_results: Optional[int] = 50

# Chat Management Models
class ChatSessionRequest(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None

class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    user_id: str
    created_at: str
    updated_at: str
    message_count: int
    last_message_preview: str
    status: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int
    timestamp: str

class DeleteResponse(BaseModel):
    success: bool
    message: str
    timestamp: str

# Global services
services = {}
workflow_ready = False
workflow_init_error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services with fast LLM availability, background workflow."""
    global workflow_ready, workflow_init_error
    try:
        logger.info("🚀 Fast startup: initializing Groq client first...")
        # Groq first for quick chat availability
        try:
            services['groq'] = AsyncGroqClient()
            logger.info(f"✅ Groq client ready (model={services['groq'].model})")
        except Exception as e:
            logger.warning(f"⚠️ Groq client unavailable: {e}")

        # Prepare workflow objects but initialize lazily in background
        services['workflow'] = DualDocumentProcessingWorkflow()
        services['embedding'] = create_embedding_backend()
        try:
            emb = services['embedding']
            model_name = getattr(emb, 'model_name', 'unknown')
            dim = getattr(emb, 'get_dimension', lambda: 'n/a')()
            logger.info(f"🧠 Embedding backend initialized: model='{model_name}' dim={dim}")
        except Exception as e:
            logger.warning(f"Embedding backend introspection failed: {e}")
        services['qdrant'] = JiraQdrantService()
        services['chat_context'] = ChatContextService()
        services['jira'] = JiraService()
        services['jira_dashboard'] = JiraDashboard(services['jira'])
        services['team_analytics'] = TeamAnalyticsService(services['jira'])
        services['resolution_assist'] = ResolutionAssistService(
            jira_service=services['jira'],
            ingestion_version="v3_resolved_flag_2025-09-30"  # Use the same version as in retrieval
        )
        # Optional ticket reranker (lazy init)
        if os.getenv('ENABLE_TICKET_RERANK', 'false').lower() in {'1','true','yes','on'}:
            services['ticket_reranker'] = ticket_reranker_service
            logger.info("🔎 Ticket reranker registered (will lazy initialize on first use)")
        else:
            logger.info("⚙️ Ticket reranker disabled (set ENABLE_TICKET_RERANK=true to enable)")

        async def _init_workflow():
            global workflow_ready, workflow_init_error
            try:
                logger.info("🏗️ Background: initializing full LangGraph workflow (embeddings, rerankers)...")
                await services['workflow'].initialize()
                
                # Initialize chat context service
                if services.get('chat_context'):
                    await services['chat_context'].initialize()
                    logger.info("✅ Chat context service initialized")
                
                # Enhance resolution assist service with embedding and qdrant for semantic search
                if services.get('resolution_assist') and services.get('embedding') and services.get('qdrant'):
                    services['resolution_assist'].embedding_service = services['embedding']
                    services['resolution_assist'].qdrant_service = services['qdrant']
                    services['resolution_assist'].semantic_enabled = True
                    logger.info("🔍 Resolution assist service enhanced with semantic search capabilities")
                
                workflow_ready = True
                logger.info("✅ Background workflow initialization complete")
            except Exception as wf_err:
                workflow_init_error = str(wf_err)
                logger.error(f"❌ Workflow initialization failed: {wf_err}")

        # Kick off background task
        asyncio.create_task(_init_workflow())
        logger.info("✅ Fast startup complete (workflow initializing in background)")
    except Exception as e:
        logger.error(f"❌ Startup sequence failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    logger.info("🔄 Shutting down LangGraph services...")
    # Add cleanup logic if needed

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    groq_info = None
    if 'groq' in services:
        try:
            groq_info = services['groq'].get_model_info()
        except Exception as e:
            groq_info = {"error": str(e)}
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "services": {
            "workflow": services.get('workflow') is not None,
            "embedding": services.get('embedding') is not None,
            "qdrant": services.get('qdrant') is not None,
            "groq": 'groq' in services,
            "chat_context": services.get('chat_context') is not None,
            "workflow_ready": workflow_ready,
            "workflow_error": workflow_init_error,
            "groq_diagnostics": groq_info,
        }
    }

# Document processing endpoints
@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document using LangGraph workflow"""
    try:
        if not services.get('workflow'):
            raise HTTPException(status_code=503, detail="LangGraph workflow not initialized")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process using LangGraph workflow
        start_time = asyncio.get_event_loop().time()
        result = await services['workflow'].process_documents()
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Extract statistics
        stats = result.get('stats', {})
        
        return DocumentUploadResponse(
            message="Document processed successfully",
            filename=file.filename,
            file_id=file_id,
            chunks_created=stats.get('chunks_created', 0),
            vectors_stored=stats.get('vectors_stored', 0)
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/process")
async def process_documents():
    """Trigger document processing for files in configured directories"""
    try:
        if not services.get('workflow'):
            raise HTTPException(status_code=503, detail="LangGraph workflow not initialized")
        
        start_time = asyncio.get_event_loop().time()
        result = await services['workflow'].process_documents()
        processing_time = asyncio.get_event_loop().time() - start_time
        
        stats = result.get('stats', {})
        
        return {
            "status": "success",
            "processing_time": processing_time,
            "documents_processed": stats.get('documents_processed', 0),
            "chunks_created": stats.get('chunks_created', 0),
            "embeddings_generated": stats.get('embeddings_generated', 0),
            "vectors_stored": stats.get('vectors_stored', 0),
            "pdf_vectors": stats.get('pdf_vectors', 0),
            "jira_vectors": stats.get('jira_vectors', 0)
        }
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoints  
@app.post("/api/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents using LangGraph workflow"""
    try:
        if not services.get('workflow'):
            raise HTTPException(status_code=503, detail="LangGraph workflow not initialized")
        
        start_time = asyncio.get_event_loop().time()
        
        # Use LangGraph workflow for search
        results = await services['workflow'].search_documents(
            query=request.query,
            collection=request.collection,
            limit=request.limit
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GET search endpoint for frontend compatibility
@app.get("/api/search")
async def search_documents_get(query: str, limit: int = 10, collection: str = None):
    """Search documents using GET method (frontend compatibility)"""
    try:
        if not services.get('workflow'):
            raise HTTPException(status_code=503, detail="LangGraph workflow not initialized")
        
        start_time = asyncio.get_event_loop().time()
        
        # Use LangGraph workflow for search
        results = await services['workflow'].search_documents(
            query=query,
            collection=collection,
            limit=limit
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/similar/{query}")
async def search_similar(query: str, limit: int = 10, collection: str = None):
    """Search for similar documents"""
    try:
        if not services.get('workflow'):
            raise HTTPException(status_code=503, detail="LangGraph workflow not initialized")
        
        start_time = asyncio.get_event_loop().time()
        
        # Use LangGraph workflow for search
        results = await services['workflow'].search_documents(
            query=query,
            collection=collection,
            limit=limit
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return {
            "query": query,
            "results": results,
            "total_results": len(results),
            "processing_time": processing_time,
            "collection": collection or "all"
        }
        
    except Exception as e:
        logger.error(f"Similar search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

LATEST_INGESTION_VERSION = "v3_resolved_flag_2025-09-30"

# In-memory record of last prompt assembly for debugging
_LAST_PROMPT_DEBUG: Dict[str, Any] = {}

async def retrieve_ticket_context(message: str, qdrant_url: str, max_tickets: int = 3, per_ticket_limit: int = 5):
    """Retrieve ticket chunks & sources from Qdrant given a user message.
    Returns (context_text, sources)."""
    # Allow alphanumeric project keys (letters+digits) before dash
    ticket_pattern = re.compile(r'[A-Z0-9]{2,10}-\d{1,7}')
    mentioned = list(set(ticket_pattern.findall(message.upper())))[:max_tickets]
    sources: List[Dict[str, Any]] = []
    if not mentioned:
        logger.info("Retrieval: no ticket pattern detected in message")
        return "", sources
    logger.info(f"Retrieval: detected tickets={mentioned}")
    retrieved_blocks = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            seen_block_ids = set()
            for tk in mentioned:
                variants = {tk, tk.lower()}
                for word in re.findall(r'[A-Za-z]{2,10}-\d{1,7}', message):
                    if word.upper() == tk:
                        variants.add(word)
                logger.info(f"Retrieval: ticket {tk} variants={variants}")
                variant_points_collected = 0
                for v in variants:
                    body = {
                        "limit": per_ticket_limit,
                        "with_payload": True,
                        "filter": {"must": [
                            {"key": "ticket_key", "match": {"value": v}},
                            {"key": "ingestion_version", "match": {"value": LATEST_INGESTION_VERSION}}
                        ]}
                    }
                    try:
                        resp = await client.post(f"{qdrant_url}/collections/jira_tickets/points/scroll", json=body)
                        if resp.status_code == 200:
                            data = resp.json()
                            points = data.get('result', {}).get('points', [])
                            if points:
                                logger.info(f"Retrieval: ticket={tk} variant={v} points={len(points)}")
                            for p in points:
                                payload = p.get('payload', {})
                                # Prefer enriched chunk text field name variants
                                chunk_body = payload.get('chunk_text') or payload.get('text','')
                                block_id = f"{payload.get('ticket_key','')}::{hash(chunk_body[:120])}"
                                if block_id in seen_block_ids:
                                    continue
                                seen_block_ids.add(block_id)
                                # Attach enriched analyses if present
                                l1 = payload.get('l1_l2_analysis')
                                l3 = payload.get('l3_engineer_analysis')
                                extra_sections = []
                                if l1:
                                    extra_sections.append(f"L1/L2: {str(l1)[:400]}")
                                if l3:
                                    extra_sections.append(f"L3: {str(l3)[:400]}")
                                analyses_text = ("\n" + "\n".join(extra_sections)) if extra_sections else ""
                                status = (payload.get('status') or '').title()
                                resolved = status in {"Done","Closed","Resolved"}
                                resolution_tag = "[RESOLVED]" if resolved else "[ACTIVE]"
                                guidance_line = "Resolution context (do NOT propose new fix)." if resolved else "Active ticket context (you may propose troubleshooting steps)."
                                block = (
                                    f"{resolution_tag} Ticket: {payload.get('ticket_key','')} | Status: {status} | Priority: {payload.get('priority','')} | Assignee: {payload.get('assignee','')}\n"
                                    f"Summary: {payload.get('summary','')}\n"
                                    f"Guidance: {guidance_line}\n"
                                    f"Snippet: {chunk_body[:600]}{analyses_text}\n---"
                                )
                                retrieved_blocks.append(block)
                                sources.append({
                                    "ticket_key": payload.get('ticket_key'),
                                    "summary": payload.get('summary'),
                                    "status": payload.get('status'),
                                    "priority": payload.get('priority'),
                                    "assignee": payload.get('assignee'),
                                    "issue_type": payload.get('issue_type'),
                                    "components": payload.get('components'),
                                    "score": p.get('score'),
                                    "variant": v,
                                    "is_resolved": payload.get('is_resolved')
                                })
                                variant_points_collected += 1
                                if variant_points_collected >= per_ticket_limit:
                                    break
                    except Exception as inner_e:
                        logger.warning(f"Retrieval: ticket {tk} variant {v} error: {inner_e}")
                if variant_points_collected == 0:
                    logger.info(f"Retrieval: no points found for ticket {tk}")
    except Exception as e:
        logger.warning(f"Retrieval: augmentation error {e}")
    if retrieved_blocks:
        context_text = "[JIRA TICKET CONTEXT]\n" + "\n".join(retrieved_blocks[:12]) + "\n[END CONTEXT]"
        logger.info(f"Retrieval: assembled blocks={len(retrieved_blocks)} sources={len(sources)}")
        return context_text, sources
    logger.info("Retrieval: no context assembled")
    return "", sources

async def semantic_ticket_search(
    query: str,
    qdrant_url: str,
    embedding_service,
    semantic_limit: int = 24,
    top_k: int = 8
) -> List[Dict[str, Any]]:
    """Hybrid semantic + lexical ticket search.

    Steps:
      1. Semantic vector search to get a broader candidate pool (semantic_limit)
      2. For each candidate compute lexical & structural features relative to query:
         - token_overlap: proportion overlap of normalized alphanumeric tokens
         - number_overlap: count of shared multi-digit numbers (>=2 digits)
         - ticket_key_match: 1.0 if query explicitly mentions the candidate key
         - semantic_norm: semantic score normalized by max score
      3. Composite score = 0.55*semantic_norm + 0.25*token_overlap + 0.15*number_overlap_norm + 0.05*ticket_key_match
         (number_overlap_norm is number_overlap divided by max number_overlap (>=1) across candidates)
      4. Return top_k candidates with added 'composite_score' and feature breakdown for debugging.

    Rationale: reduces cases where close vector neighbors with similar wording but mismatched numeric identifiers outrank the correct ticket (e.g., mis-picking 8756 vs 9056).
    """
    import re
    from math import isfinite

    try:
        # --- Step 1: Semantic candidate retrieval ---
        vector = embedding_service.get_embeddings([query])[0]
        async with httpx.AsyncClient(timeout=20.0) as client:
            body = {
                "vector": vector,
                "limit": semantic_limit,
                "with_payload": True,
                "filter": {"must": [
                    {"key": "ingestion_version", "match": {"value": LATEST_INGESTION_VERSION}}
                ]}
            }
            resp = await client.post(f"{qdrant_url}/collections/jira_tickets/points/search", json=body)
            if resp.status_code != 200:
                logger.warning(f"Semantic search HTTP {resp.status_code}: {resp.text[:160]}")
                return []
            raw_hits = resp.json().get('result', [])
            if not raw_hits:
                return []

        # --- Step 2: Feature extraction ---
        q_tokens = re.findall(r"[A-Za-z0-9]+", query.lower())
        q_token_set = set(q_tokens)
        q_numbers = set(re.findall(r"\d{2,}", query))
        ticket_key_pattern = re.compile(r"[A-Z0-9]{2,10}-\d{1,7}")
        mentioned_keys = set(ticket_key_pattern.findall(query.upper()))

        candidates = []
        max_sem_score = max(h.get('score', 0.0) for h in raw_hits) or 1.0
        number_overlap_values = []

        for h in raw_hits:
            payload = h.get('payload', {}) or {}
            sem_score = h.get('score', 0.0)
            summary = payload.get('summary') or ''
            chunk_text = payload.get('chunk_text') or payload.get('text') or ''
            ticket_key = (payload.get('ticket_key') or '').upper()
            cand_text = f"{summary} {chunk_text[:400]} {ticket_key}".lower()
            c_tokens = set(re.findall(r"[A-Za-z0-9]+", cand_text))
            overlap_tokens = len(q_token_set & c_tokens)
            token_overlap = overlap_tokens / (len(q_token_set) + 1)
            cand_numbers = set(re.findall(r"\d{2,}", cand_text))
            number_overlap = len(q_numbers & cand_numbers)
            ticket_key_match = 1.0 if ticket_key in mentioned_keys and ticket_key else 0.0
            semantic_norm = sem_score / max_sem_score if max_sem_score else 0.0
            number_overlap_values.append(number_overlap)
            candidates.append({
                "payload": payload,
                "semantic_score": sem_score,
                "semantic_norm": semantic_norm,
                "token_overlap": token_overlap,
                "number_overlap": number_overlap,
                "ticket_key_match": ticket_key_match
            })

        max_num_overlap = max(number_overlap_values) if number_overlap_values else 0
        if max_num_overlap < 1:
            max_num_overlap = 1  # avoid div by zero

        # --- Step 3: Composite scoring ---
        for c in candidates:
            number_overlap_norm = c['number_overlap'] / max_num_overlap
            composite = (
                0.55 * c['semantic_norm'] +
                0.25 * c['token_overlap'] +
                0.15 * number_overlap_norm +
                0.05 * c['ticket_key_match']
            )
            c['composite_score'] = composite

        candidates.sort(key=lambda x: x['composite_score'], reverse=True)
        pre_rerank_top = candidates[: min(len(candidates), max(top_k*2, 12))]

        # --- Step 4 (optional): Cross-encoder reranking if enabled ---
        from math import isfinite  # already imported but safe
        rerank_used = False
        if 'ticket_reranker' in services:
            try:
                reranker = services['ticket_reranker']
                # Build lightweight docs list for reranker
                docs_for_rerank = []
                for cand in pre_rerank_top:
                    pl = cand['payload']
                    docs_for_rerank.append({
                        'ticket_key': pl.get('ticket_key'),
                        'summary': pl.get('summary'),
                        'content': (pl.get('chunk_text') or pl.get('text') or '')[:600]
                    })
                # Perform reranking
                reranked = await reranker.rerank_async(query, docs_for_rerank, top_k=top_k)
                # Map rerank scores back
                rerank_map = {r.get('ticket_key'): r.get('rerank_score') for r in reranked}
                for cand in pre_rerank_top:
                    tk = cand['payload'].get('ticket_key')
                    if tk in rerank_map:
                        cand['rerank_score'] = rerank_map[tk]
                # Sort primarily by rerank_score then composite fallback
                pre_rerank_top.sort(key=lambda c: (c.get('rerank_score', -1), c['composite_score']), reverse=True)
                rerank_used = True
            except Exception as rr_err:
                logger.warning(f"SemanticHybrid: reranker failed {rr_err}")
        top_candidates = pre_rerank_top[:top_k]

        results: List[Dict[str, Any]] = []
        debug_lines = []
        for c in top_candidates:
            payload = dict(c['payload'])  # shallow copy
            # Preserve original semantic score field name for backward compatibility
            payload['score'] = c['semantic_score']
            payload['composite_score'] = c['composite_score']
            if 'rerank_score' in c:
                payload['rerank_score'] = c['rerank_score']
            payload['_features'] = {
                'semantic_norm': round(c['semantic_norm'], 4),
                'token_overlap': round(c['token_overlap'], 4),
                'number_overlap': c['number_overlap'],
                'ticket_key_match': c['ticket_key_match']
            }
            results.append(payload)
            debug_lines.append(
                f"{payload.get('ticket_key')} {'RR=' + format(payload.get('rerank_score'),'.3f') if 'rerank_score' in payload else ''} comp={payload['composite_score']:.3f} sem={c['semantic_norm']:.3f} tok={c['token_overlap']:.3f} num={c['number_overlap']} key={c['ticket_key_match']:.0f}"
            )

        if debug_lines:
            prefix = "SemanticHybrid+RR" if rerank_used else "SemanticHybrid"
            logger.info(prefix + ": " + " | ".join(debug_lines))
        return results

    except Exception as e:
        logger.warning(f"Semantic hybrid search error: {e}")
        return []

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with optional streaming using Groq + RAG sources + conversation history."""
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # --- Retrieve conversation history for context ---
        chat_history = ""
        chat_context_service = services.get('chat_context')
        if chat_context_service and request.session_id:
            # Get existing conversation history
            history_messages = await chat_context_service.get_chat_history(session_id, limit=10)
            if history_messages:
                chat_history = chat_context_service.format_chat_history_for_context(history_messages)
                logger.info(f"Retrieved {len(history_messages)} messages for session context")

        # --- Retrieval Augmentation (simple ticket-based) ---
        context_text = ""
        sources: List[Dict[str, Any]] = []
        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        context_text, sources = await retrieve_ticket_context(request.message, qdrant_url)
        # If no ticket context, attempt semantic retrieval on jira tickets
        if not context_text and not request.fast:
            embedding_service = services.get('embedding')
            if embedding_service:
                sem_hits = await semantic_ticket_search(request.message, qdrant_url, embedding_service)
                if sem_hits:
                    sem_blocks = []
                    for h in sem_hits[:6]:
                        # Build context with L3 engineer analysis (contains the actual solution!)
                        l3_analysis = h.get('l3_engineer_analysis', '') or ''
                        l1_l2_analysis = h.get('l1_l2_analysis', '') or ''
                        
                        # Always include L3 analysis when available - this is the key fix!
                        if request.legacy_mode:
                            # Legacy simpler formatting
                            sem_blocks.append(
                                f"[SEM] Ticket: {h.get('ticket_key')} | Status: {h.get('status')}\n"
                                f"Summary: {h.get('summary','')}\n"
                                f"Snippet: {(h.get('chunk_text') or '')[:300]}\n"
                                f"L3 Solution: {l3_analysis.strip()[:500] if l3_analysis.strip() else 'No L3 analysis available'}\n---"
                            )
                        else:
                            sem_blocks.append(
                                f"[SEM] Ticket: {h.get('ticket_key')} | Status: {h.get('status')} | CompScore: {h.get('composite_score',0):.3f} | SemScore: {h.get('score'):.3f}\n"
                                f"Summary: {h.get('summary','')}\n" 
                                f"Snippet: {(h.get('chunk_text') or '')[:300]}\n"
                                f"L3 Solution: {l3_analysis.strip()[:500] if l3_analysis.strip() else 'No L3 analysis available'}\n---"
                            )
                        src_obj = {
                            "ticket_key": h.get('ticket_key'),
                            "summary": h.get('summary'),
                            "status": h.get('status'),
                            "priority": h.get('priority'),
                            "assignee": h.get('assignee'),
                            "issue_type": h.get('issue_type'),
                            "components": h.get('components'),
                            "score": h.get('score'),
                            "variant": "semantic_hybrid" if not request.legacy_mode else "semantic_legacy",
                            "is_resolved": h.get('is_resolved')
                        }
                        if not request.legacy_mode:
                            src_obj["composite_score"] = h.get('composite_score')
                            if 'rerank_score' in h:
                                src_obj['rerank_score'] = h.get('rerank_score')
                        sources.append(src_obj)
                    context_text = "[SEMANTIC JIRA CONTEXT]\n" + "\n".join(sem_blocks) + "\n[END CONTEXT]"

        # Combine chat history with RAG context
        full_context = chat_history + context_text

        # If Groq not initialized, return graceful fallback
        if 'groq' not in services:
            return ChatResponse(
                response="LLM not configured (missing GROQ_API_KEY). Backend otherwise healthy.",
                sources=sources,
                session_id=session_id,
                timestamp=datetime.now().isoformat()
            )

        # Build final system prompt: base system + optional user custom (guardrails embedded in base now)
        from .prompt_templates import system_prompt_chat
        base_system = system_prompt_chat()
        parts = [base_system]
        if request.use_custom_prompt and request.custom_system_prompt:
            parts.append("---\n" + request.custom_system_prompt)
        combined_system_prompt = "\n\n".join(p for p in parts if p)

        # Generate response (streaming or non-streaming)
        if request.stream:
            async def token_generator():
                collected = ""
                async for token in services['groq'].generate_response_stream_async(
                    query=request.message,
                    context=full_context,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                    model=request.model,
                    mode='chat',
                    use_custom_prompt=True,
                    custom_system_prompt=combined_system_prompt,
                ):
                    collected += token
                    yield token
                
                # Store the conversation in chat context after streaming is complete
                if chat_context_service:
                    try:
                        await chat_context_service.add_message(session_id, request.message, collected, sources)
                    except Exception as e:
                        logger.warning(f"Failed to store streamed conversation: {e}")
                
                # After stream ends, we append a JSON delimiter message (client can ignore if treating raw tokens)
                meta = json.dumps({
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "complete": True
                })
                yield f"\n[[STREAM_DONE]]{meta}"

            return StreamingResponse(token_generator(), media_type="text/plain")

        # Non-streaming path
        answer = await services['groq'].generate_response_async(
            query=request.message,
            context=full_context,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            model=request.model,
            mode='chat',
            use_custom_prompt=True,
            custom_system_prompt=combined_system_prompt,
        )

        # Store the conversation in chat context
        if chat_context_service:
            try:
                await chat_context_service.add_message(session_id, request.message, answer, sources)
                logger.info(f"Stored conversation for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to store conversation: {e}")

        # Save debug info
        try:
            _LAST_PROMPT_DEBUG.update({
                'session_id': session_id,
                'user_message': request.message,
                'chat_history': chat_history,
                'rag_context': context_text,
                'final_context': full_context,
                'sources': sources,
                'system_prompt': combined_system_prompt,
                'system_prompt_includes_base': True,
                'timestamp': datetime.now().isoformat()
            })
        except Exception:
            pass

        return ChatResponse(
            response=answer,
            sources=sources,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# JIRA Assist Endpoint
@app.get("/api/jira/assist/{ticket_key}", response_model=JiraAssistResponse)
async def jira_assist(ticket_key: str, max_refs: int = 5):
        """Provide suggested resolution guidance for an unresolved ticket by leveraging resolved tickets.
        Steps:
          1. Fetch ticket details via JiraService.
          2. If already resolved -> return summary only.
          3. Otherwise, semantic retrieval of resolved tickets (current simplistic: filter points where is_resolved=true and same components or project).
          4. Build a guidance prompt and call LLM.
        """
        if 'groq' not in services or 'jira' not in services:
            raise HTTPException(status_code=503, detail="Required services not initialized")
        jira_service: JiraService = services['jira']
        if not jira_service.is_available():
            raise HTTPException(status_code=503, detail="JIRA service not configured")
        # 1. Ticket details
        details = await jira_service.get_ticket_details(ticket_key)
        if not details:
            raise HTTPException(status_code=404, detail="Ticket not found")
        status = (details.get('status') or '').title()
        # 2. If resolved, summarise only
        resolved_statuses = {"Done","Closed","Resolved"}
        if status in resolved_statuses:
            summary_prompt = (
                f"Provide a concise resolution summary for resolved ticket {ticket_key}. Include key fix actions."
            )
            suggestion = await services['groq'].generate_response_async(
                query=summary_prompt,
                context=f"Summary: {details.get('summary','')}\nDescription: {details.get('description','')[:1500]}",
                temperature=0.3,
                max_tokens=400,
                top_p=0.9,
                model=os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile'),
                 mode='assist',
                use_custom_prompt=True,
                custom_system_prompt="You summarize already-resolved JIRA tickets precisely without proposing new steps."
            )
            return JiraAssistResponse(
                ticket_key=ticket_key,
                status=status,
                resolved_reference_count=0,
                references=[],
                suggestion=suggestion
            )
        # 3. Retrieve resolved references from Qdrant (simple scroll filter). Could be improved with embedding similarity.
        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        refs: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                body = {
                    "limit": 200,
                    "with_payload": True,
                    "filter": {"must": [
                        {"key": "is_resolved", "match": {"value": True}},
                        {"key": "ingestion_version", "match": {"value": LATEST_INGESTION_VERSION}}
                    ]}
                }
                resp = await client.post(f"{qdrant_url}/collections/jira_tickets/points/scroll", json=body)
                if resp.status_code == 200:
                    points = resp.json().get('result', {}).get('points', [])
                    # Basic relevance heuristic: same project keyword overlap in summary
                    target_words = set(details.get('summary','').lower().split())
                    scored = []
                    for p in points:
                        pl = p.get('payload', {})
                        summary = (pl.get('summary') or '').lower()
                        overlap = len(target_words & set(summary.split()))
                        scored.append((overlap, pl))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    for overlap, pl in scored[:max_refs]:
                        refs.append({
                            "ticket_key": pl.get('ticket_key'),
                            "status": pl.get('status'),
                            "summary": pl.get('summary'),
                            "l1_l2_analysis": pl.get('l1_l2_analysis'),
                            "l3_engineer_analysis": pl.get('l3_engineer_analysis'),
                            "overlap": overlap
                        })
        except Exception as e:
            logger.warning(f"Assist reference retrieval failed: {e}")

        # 4. Build suggestion prompt
        reference_context_parts = []
        for r in refs:
            reference_context_parts.append(
                f"Ref {r['ticket_key']} (Status {r['status']}): {r.get('summary','')}. L1/L2: {(r.get('l1_l2_analysis') or '')[:300]} L3: {(r.get('l3_engineer_analysis') or '')[:300]}"
            )
        reference_context = "\n".join(reference_context_parts)[:6000]
        prompt_query = build_user_prompt_prioritized_troubleshoot(
            ticket_key=ticket_key,
            condensed_issue=(details.get('summary','') or '')[:300],
            reference_snippets=reference_context_parts[:5]
        )
        system_prompt = system_prompt_prioritized_troubleshoot()
        suggestion = await services['groq'].generate_response_async(
            query=prompt_query,
            context=f"Unresolved Ticket Summary: {details.get('summary','')}\nDescription: {details.get('description','')[:1500]}\n\nResolved References:\n{reference_context}",
            temperature=0.4,
            max_tokens=600,
            top_p=0.9,
            model=os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile'),
              mode='assist',
            use_custom_prompt=True,
            custom_system_prompt=system_prompt
        )
        return JiraAssistResponse(
            ticket_key=ticket_key,
            status=status,
            resolved_reference_count=len(refs),
            references=refs,
            suggestion=suggestion
        )

# Collections endpoint
@app.get("/api/collections")
async def list_collections():
    """List available collections"""
    try:
        if not services.get('qdrant'):
            raise HTTPException(status_code=503, detail="Qdrant service not initialized")
        
        # Get collection info from Qdrant
        collections = await services['qdrant'].list_collections()
        
        return {
            "collections": collections,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Collections list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Stats endpoint
@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        stats = {
            "system": {
                "status": "operational",
                "version": "3.0.0",
                "timestamp": datetime.now().isoformat()
            },
            "services": {
                "langgraph_workflow": services.get('workflow') is not None,
                "embedding_bge": services.get('embedding') is not None,
                "qdrant": services.get('qdrant') is not None,
            }
        }
        
        if services.get('qdrant'):
            # Add collection stats
            try:
                collections = await services['qdrant'].list_collections()
                stats["collections"] = collections
            except:
                stats["collections"] = []
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# JIRA Dashboard Endpoints
@app.get("/api/jira/filters")
async def get_jira_filters():
    """Get JIRA filter options for dropdowns"""
    try:
        if not services.get('jira_dashboard'):
            raise HTTPException(status_code=503, detail="JIRA dashboard service not initialized")
        
        filters = await services['jira_dashboard'].get_filter_options()
        return filters
        
    except Exception as e:
        logger.error(f"JIRA filters error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jira/search")
async def search_jira_tickets(request: JiraSearchRequest):
    """Search JIRA tickets with filters"""
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        
        tickets = await services['jira'].search_tickets(
            query=request.query,
            assignee=request.assignee,
            status=request.status,
            priority=request.priority,
            max_results=request.max_results or 50
        )
        
        return {
            "tickets": tickets,
            "total_count": len(tickets),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"JIRA search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/search")
async def search_jira_tickets_get(
    page: int = 1, 
    limit: int = 20, 
    query: str = None, 
    assignee: str = None, 
    status: str = None, 
    priority: str = None, 
    custom_jql: str = None
):
    """Search JIRA tickets with filters (GET method for frontend compatibility)"""
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        
        # Calculate max_results based on page and limit
        max_results = page * limit
        
        tickets = await services['jira'].search_tickets(
            query=query,
            assignee=assignee,
            status=status,
            priority=priority,
            custom_jql=custom_jql,
            max_results=max_results
        )
        
        # Calculate pagination
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_tickets = tickets[start_index:end_index]
        
        return {
            "tickets": paginated_tickets,
            "total_count": len(tickets),
            "page": page,
            "limit": limit,
            "total_pages": (len(tickets) + limit - 1) // limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"JIRA search GET error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/ticket/{ticket_key}")
async def get_jira_ticket(ticket_key: str):
    """Get detailed JIRA ticket information"""
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        
        ticket = await services['jira'].get_ticket_details(ticket_key)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JIRA ticket details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jira/ticket")
async def create_jira_ticket(request: JiraTicketRequest):
    """Create a new JIRA ticket"""
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        
        result = await services['jira'].create_ticket(
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            issue_type=request.issue_type
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create ticket")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JIRA ticket creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jira/comment")
async def add_jira_comment(request: JiraCommentRequest):
    """Add comment to JIRA ticket"""
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        
        success = await services['jira'].add_comment_to_ticket(
            ticket_key=request.ticket_key,
            comment=request.comment
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add comment")
        
        return {
            "success": True,
            "message": "Comment added successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JIRA comment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/dashboard/stats")
async def get_jira_dashboard_stats():
    """Get JIRA dashboard statistics"""
    try:
        if not services.get('jira_dashboard'):
            raise HTTPException(status_code=503, detail="JIRA dashboard service not initialized")
        
        # Get basic stats
        stats = await services['jira_dashboard'].get_dashboard_data()
        return stats
        
    except Exception as e:
        logger.error(f"JIRA dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/dashboard")
async def get_jira_dashboard(project_filter: str = Query('ALL'), date_range: str = Query('7d')):
    """Aggregate dashboard data in shape expected by legacy frontend JiraPanel.

    Adds keys:
      summary.mbsl3_open, summary.uno_open, mbsl3_status, recent_tickets
    Derived from existing JiraDashboard stats (project = MBSL3 and UNO component counts).
    """
    try:
        if not services.get('jira_dashboard'):
            raise HTTPException(status_code=503, detail="JIRA dashboard service not initialized")
        raw = await services['jira_dashboard'].get_dashboard_data(project_filter=project_filter, date_range=date_range)
        if 'error' in raw:
            return raw
    # Derive mbsl3_open and uno_open from status/component distributions (legacy UI expectation)
        # Assume tickets with component including 'UNO' counted as UNO open if status in active set
        active_statuses = {'Open','In Progress','To Do','In Review','Testing','L3 Analysis','GCS'}
        mbsl3_status = raw.get('status_distribution', {})
        # Count UNO open tickets from recent_tickets list
        uno_open = 0
        for t in raw.get('recent_tickets', []):
            comps = t.get('component', []) or []
            if any(c.upper() == 'UNO' for c in comps) and t.get('status') in active_statuses:
                uno_open += 1
        # Approximate mbsl3_open as active_tickets from summary
        mbsl3_open = raw.get('summary', {}).get('active_tickets', 0)
        # Embed into shape
        raw.setdefault('summary', {})['mbsl3_open'] = mbsl3_open
        raw['summary']['uno_open'] = uno_open
        raw['mbsl3_status'] = mbsl3_status
        return raw
    except Exception as e:
        logger.error(f"JIRA dashboard aggregate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/projects")
async def get_jira_projects():
    """Return list of available JIRA projects (basic). Derives from recent tickets as fallback.

    Shape: {"projects": [{"key": "MBSL3", "name": "MBSL3"}, ...]}
    """
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")
        # Attempt to use JiraService method if exists
        jira = services['jira']
        projects = []
        if hasattr(jira, 'get_projects'):
            try:
                raw = await jira.get_projects()
                for p in raw:
                    key = p.get('key') or p.get('id') or 'UNKNOWN'
                    name = p.get('name') or key
                    projects.append({"key": key, "name": name})
            except Exception as e:
                logger.warning(f"get_projects failed: {e}; falling back to ticket-derived projects")
        if not projects:
            # Fallback: derive from tickets in main project space
            sample = await jira.search_tickets(custom_jql='ORDER BY updated DESC', max_results=200)
            keys = set()
            for t in sample:
                # Extract project part before '-'
                ticket_key = t.get('key')
                if ticket_key and '-' in ticket_key:
                    proj = ticket_key.split('-',1)[0]
                    keys.add(proj)
            for k in sorted(keys):
                projects.append({"key": k, "name": k})
        return {"projects": projects, "count": len(projects)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JIRA projects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/status")
async def get_jira_status():
    """Check JIRA service status"""
    try:
        jira_available = services.get('jira') and services['jira'].is_available()
        
        return {
            "available": jira_available,
            "status": "connected" if jira_available else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"JIRA status error: {e}")
        return {
            "available": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Team Analytics Endpoints
@app.get("/api/jira/team-analytics")
async def get_team_analytics(
    date_range: str = Query("30d", alias="date_range"),  # accept ?date_range=
    custom_jql: str = None,
    jql: str = Query(None, alias="jql"),
    max_results: int = 2000
):
    """Get team analytics formatted for UI.

    The newer frontend expects a shape like:
      {
        summary_cards: [...],
        individual_performance: [...],
        productivity_insights: [...]
      }

    Original service returns:
      { team_summary: {...}, individual_performance: [...] }

    We adapt & enrich without breaking legacy clients by also returning raw_analytics.
    """
    try:
        if not services.get('team_analytics'):
            raise HTTPException(status_code=503, detail="Team analytics service not initialized")

        # Support alternate param names (?date_range= & ?jql=)
        effective_range = date_range or "30d"
        effective_jql = jql or custom_jql

        raw = await services['team_analytics'].get_team_analytics(
            date_range=effective_range,
            custom_jql=effective_jql,
            max_results=max_results
        )

        if isinstance(raw, dict) and raw.get("error"):
            raise HTTPException(status_code=500, detail=raw.get("detail", "analytics_error"))

        team_summary = raw.get('team_summary', {})
        members = raw.get('individual_performance', []) or []
        team_overview = raw.get('team_overview', {}) or {}
        trend_metrics = raw.get('trend_metrics', {}) or {}
        forecast = raw.get('forecast', {}) or {}
        risk_alerts = raw.get('risk_alerts', []) or []

        # Build summary cards to match frontend styling (values as display strings)
        summary_cards = [
            {
                "title": "Team Members",
                "value": str(team_summary.get('team_members', 0)),
                "subtitle": "Active contributors",
                "color": "blue"
            },
            {
                "title": "Total Tickets",
                "value": str(team_summary.get('total_tickets', 0)),
                "subtitle": "Last 30 days" if effective_range == '30d' else f"Range: {effective_range}",
                "color": "green"
            },
            {
                "title": "Avg Completion",
                "value": f"{team_summary.get('avg_completion_rate', 0)}%",
                "subtitle": "Team average",
                "color": "purple"
            },
            {
                "title": "Avg Resolution",
                "value": f"{team_summary.get('avg_resolution_days', 0)}d",
                "subtitle": "Days to complete",
                "color": "orange"
            }
        ]

        if team_summary.get('open_high_priority') is not None:
            summary_cards.append({
                "title": "High Priority Open",
                "value": str(team_summary.get('open_high_priority', 0)),
                "subtitle": "Critical backlog",
                "color": "red"
            })

        if forecast:
            summary_cards.append({
                "title": "Projected New (7d)",
                "value": str(forecast.get('projected_new_tickets', 0)),
                "subtitle": "AI workload forecast",
                "color": "cyan"
            })
            summary_cards.append({
                "title": "Effort (hrs, 7d)",
                "value": str(forecast.get('estimated_effort_hours', 0)),
                "subtitle": "Estimated delivery effort",
                "color": "pink"
            })

        # Enrich individual performance with expected keys
        enriched_members = []
        for m in members:
            enriched_members.append({
                "assignee": m.get('assignee'),
                "productivity_score": m.get('score', 0),
                "completion_rate": m.get('completion_rate', 0),
                # Basic trend heuristic: high completion & many done -> improving, low completion -> declining
                "performance_trend": (
                    'improving' if m.get('completion_rate', 0) >= 80 else (
                        'declining' if m.get('completion_rate', 0) < 50 else 'stable'
                    )
                ),
                "metrics": {
                    "done": m.get('done', 0),
                    "in_progress": m.get('progress', 0),
                    "todo": m.get('todo', 0)
                }
            })

        # Generate lightweight productivity insights (can be replaced by AI later)
        insights = []
        for m in enriched_members:
            user_insights = []
            cr = m.get('completion_rate', 0)
            done = m.get('metrics', {}).get('done', 0)
            progress = m.get('metrics', {}).get('in_progress', 0)
            todo = m.get('metrics', {}).get('todo', 0)
            total = done + progress + todo
            if cr >= 85 and done >= 5:
                user_insights.append({"type": "positive", "message": "High completion rate with strong throughput"})
            if progress > todo and progress >= 5:
                user_insights.append({"type": "info", "message": "Multiple active tasks – monitor focus"})
            if cr < 50 and total >= 5:
                user_insights.append({"type": "warning", "message": "Low completion rate – potential workload or blockers"})
            if not user_insights:
                user_insights.append({"type": "info", "message": "Steady performance"})
            insights.append({"assignee": m['assignee'], "insights": user_insights})

        team_insights = []
        for note in forecast.get('notes', []) or []:
            team_insights.append({
                "type": "forecast",
                "message": note
            })

        for alert in risk_alerts:
            team_insights.append({
                "type": alert.get('severity', 'info'),
                "message": alert.get('message'),
                "meta": {
                    "title": alert.get('title'),
                    "metric": alert.get('metric'),
                    "value": alert.get('value')
                }
            })

        ai_forecast = {
            "projected_new_tickets": forecast.get('projected_new_tickets', 0),
            "projected_completed_tickets": forecast.get('projected_completed_tickets', 0),
            "backlog_delta_next_7_days": forecast.get('backlog_delta_next_7_days', 0),
            "backlog_trend": forecast.get('backlog_trend', 'stable'),
            "estimated_effort_hours": forecast.get('estimated_effort_hours', 0),
            "confidence": forecast.get('confidence', 'low'),
            "notes": forecast.get('notes', []) or []
        }

        payload = {
            "summary_cards": summary_cards,
            "individual_performance": enriched_members,
            "productivity_insights": insights,
            "team_overview": team_overview,
            "trend_metrics": trend_metrics,
            "ai_forecast": ai_forecast,
            "team_insights": team_insights,
            "raw_analytics": raw,
            "timestamp": datetime.now().isoformat()
        }
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Team analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/team-analytics/{assignee}")
async def get_individual_analytics(assignee: str, date_range: str = "30d"):
    """Get individual team member analytics"""
    try:
        if not services.get('team_analytics'):
            raise HTTPException(status_code=503, detail="Team analytics service not initialized")
        
        analytics = await services['team_analytics'].get_individual_deep_dive(
            assignee=assignee,
            date_range=date_range
        )
        
        if "error" in analytics:
            raise HTTPException(status_code=500, detail=analytics["detail"])
        
        return {
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Individual analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New endpoint used by frontend (expects different shape)
@app.get("/api/jira/individual-analysis/{assignee}")
async def get_individual_analysis_frontend(assignee: str, date_range: str = Query("30d", alias="date_range")):
    """Frontend specific individual analysis shape.

    Returns:
      {
        performance_summary: { completion_rate, avg_resolution_days, status_breakdown, productivity_insights: [...] },
        status_timeline: [ { key, status, summary, updated, url } ... ]
      }
    """
    try:
        if not services.get('team_analytics'):
            raise HTTPException(status_code=503, detail="Team analytics service not initialized")

        raw = await services['team_analytics'].get_individual_deep_dive(
            assignee=assignee,
            date_range=date_range
        )
        if isinstance(raw, dict) and raw.get('error'):
            raise HTTPException(status_code=500, detail=raw.get('detail', 'analysis_error'))

        stats = raw.get('stats', {})
        tickets = raw.get('tickets', [])

        status_breakdown = {}
        for t in tickets:
            status_breakdown[t.get('status') or 'Unknown'] = status_breakdown.get(t.get('status') or 'Unknown', 0) + 1

        # Simple heuristic insights
        insights = []
        cr = stats.get('completion_rate', 0)
        if cr >= 85:
            insights.append("Excellent completion rate this period")
        elif cr >= 70:
            insights.append("Solid completion rate – maintain momentum")
        else:
            insights.append("Completion rate could improve – review blockers")
        if stats.get('avg_resolution_days', 0) > 5:
            insights.append("Resolution time above target – prioritize faster closure of tasks")
        else:
            insights.append("Resolution time within healthy range")

        performance_summary = {
            "completion_rate": stats.get('completion_rate', 0),
            "avg_resolution_days": stats.get('avg_resolution_days', 0),
            "status_breakdown": status_breakdown,
            "productivity_insights": insights
        }

        # Map tickets into timeline (updated not available in raw, so use resolved or created)
        timeline = []
        for t in tickets:
            timeline.append({
                "key": t.get('key'),
                "summary": t.get('summary'),
                "status": t.get('status'),
                "priority": t.get('priority'),
                "updated": t.get('resolved') or t.get('created'),
                "url": f"https://jira/browse/{t.get('key')}" if t.get('key') else None
            })

        return {
            "performance_summary": performance_summary,
            "status_timeline": timeline,
            "raw": raw,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Individual analysis (frontend) error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/live/summary")
async def get_live_summary(project_filter: str = "ALL", date_range: str = "7d", quick_filter: str = None):
    """Get live JIRA dashboard summary data.

    Optional quick_filter values (maps to JQL before stats aggregation):
      - ACTIVE_MBSL3 -> project = "MBSL3" AND status != "Done"
      - RECENT_UPDATES -> project = "MBSL3" AND updated >= -7d
      - HIGH_PRIORITY -> project = "MBSL3" AND priority = "High"
    """
    try:
        if not services.get('jira_dashboard'):
            raise HTTPException(status_code=503, detail="JIRA dashboard service not initialized")
        # Quick filter mapping -> custom JQL for dashboard service
        quick_map = {
            'ACTIVE_MBSL3': 'project = "MBSL3" AND status != "Done"',
            'RECENT_UPDATES': 'project = "MBSL3" AND updated >= -7d',
            'HIGH_PRIORITY': 'project = "MBSL3" AND priority = "High"'
        }
        custom_jql = quick_map.get(quick_filter) if quick_filter else None

        # Extend jira_dashboard service to accept optional custom_jql if present
        summary = await services['jira_dashboard'].get_dashboard_data(
            project_filter=project_filter,
            date_range=date_range,
            custom_jql=custom_jql
        )
        
        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])
        
        # Provide backward-compatible flat fields for existing frontend code
        flat = summary.get('summary', {}) if isinstance(summary, dict) else {}
        response = {
            "summary": summary,
            "applied_quick_filter": quick_filter,
            "timestamp": datetime.now().isoformat(),
            # Flat mirrors
            "total": flat.get('total_tickets'),
            "period_total": flat.get('period_total'),
            "overall_total": flat.get('overall_total'),
            "active": flat.get('active_tickets'),
            "resolved": flat.get('resolved_tickets'),
            "active_pct": flat.get('active_percentage'),
            "resolved_pct": flat.get('resolved_percentage'),
            "recent_updates": flat.get('recent_updates'),
        }
        # Also bubble up distributions if present
        for k in ["status_distribution","priority_distribution","assignee_distribution","type_distribution","component_distribution","recent_tickets"]:
            if k in summary:
                response[k] = summary[k]
        # Provide an assignee_top list (name,count) for legacy mapping if not already there
        if 'assignee_distribution' in summary and 'assignee_top' not in response:
            dist = summary['assignee_distribution'] or {}
            response['assignee_top'] = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:15]
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jira/recent")
async def get_recent_activity(project_key: str = "MBSL3", limit: int = 20, quick_filter: str = None):
    """Fast recent activity endpoint used by dashboard RecentActivity component.

    Parameters:
      project_key: JIRA project key (default MBSL3)
      limit: number of tickets to return (default 20, max 100)
      quick_filter: optional quick filter key matching live summary endpoint
        - ACTIVE_MBSL3
        - RECENT_UPDATES
        - HIGH_PRIORITY

    Returns:
      { tickets: [...], total: n, project: project_key, applied_quick_filter, timestamp }
    """
    try:
        if not services.get('jira'):
            raise HTTPException(status_code=503, detail="JIRA service not initialized")

        # Map quick filters to JQL (reuse same mapping as live summary)
        quick_map = {
            'ACTIVE_MBSL3': 'project = "MBSL3" AND status != "Done"',
            'RECENT_UPDATES': 'project = "MBSL3" AND updated >= -7d',
            'HIGH_PRIORITY': 'project = "MBSL3" AND priority = "High"'
        }
        if quick_filter and quick_filter not in quick_map:
            raise HTTPException(status_code=400, detail="Invalid quick_filter value")

        base_jql = quick_map.get(quick_filter)
        if not base_jql:
            # Basic recent activity ordering by updated time
            base_jql = f'project = "{project_key}" ORDER BY updated DESC'
        else:
            # Ensure ordering present
            if 'ORDER BY' not in base_jql:
                base_jql = base_jql + ' ORDER BY updated DESC'

        safe_limit = max(1, min(limit, 100))
        tickets = await services['jira'].search_tickets(custom_jql=base_jql, max_results=safe_limit)

        return {
            'tickets': tickets[:safe_limit],
            'total': len(tickets),
            'project': project_key,
            'applied_quick_filter': quick_filter,
            'timestamp': datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recent activity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# JIRA Analysis Endpoint
@app.post("/api/jira/analyze", response_model=JiraAnalyzeResponse)
async def analyze_jira_ticket(request: JiraAnalyzeRequest):
    """
    Advanced AI-powered analysis of JIRA tickets for resolution guidance.
    
    Features:
    - Robust data extraction handling inconsistent/noisy ticket formats  
    - Smart field detection (handles missing L1/L2 Analysis gracefully)
    - Semantic search over resolved tickets for similar issue patterns
    - AI-generated analysis with confidence scoring
    - Structured troubleshooting steps extraction
    
    For unresolved tickets:
    - Extracts clean ticket data from multiple potential sources
    - Searches similar resolved tickets using hybrid semantic/lexical matching
    - Provides AI-generated troubleshooting steps and technical analysis
    - Handles cases with/without existing L1/L2 analysis
    
    For resolved tickets:
    - Provides summary of resolution approach and lessons learned
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check service availability
        if not services.get('resolution_assist'):
            raise HTTPException(status_code=503, detail="Resolution assist service not initialized")
        
        if not services.get('groq'):
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Get raw ticket details first
        jira_service = services['jira']
        ticket_details = await jira_service.get_ticket_details(request.ticket_key)
        
        if not ticket_details:
            raise HTTPException(status_code=404, detail=f"Ticket {request.ticket_key} not found")
        
        # Extract and clean ticket data using our robust extractor
        extracted_data = ticket_data_extractor.extract_ticket_content(ticket_details)
        clean_context = ticket_data_extractor.get_ticket_context_for_analysis(ticket_details)
        
        logger.info(f"Analyze {request.ticket_key}: has_description={extracted_data['has_description']}, has_analysis={extracted_data['has_analysis']}")
        
        # Initialize ResolutionAssistService with embedding and qdrant if available  
        resolution_service = services['resolution_assist']
        if services.get('embedding') and services.get('qdrant') and request.include_semantic_search:
            resolution_service.embedding_service = services['embedding']
            resolution_service.qdrant_service = services['qdrant']
            resolution_service.semantic_enabled = True
            logger.info(f"🔍 Semantic search enabled for ticket analysis: {request.ticket_key}")
        else:
            resolution_service.semantic_enabled = False
            logger.info(f"📝 Using lexical search for ticket analysis: {request.ticket_key}")
        
        # Get the resolution assistance
        result = await resolution_service.assist(
            ticket_key=request.ticket_key,
            groq_client=services['groq'],
            max_refs=request.max_references
        )
        
        # Enhance the analysis with custom prompt if we have good data
        if extracted_data['has_description'] or extracted_data['has_analysis']:
            enhanced_analysis = await _generate_enhanced_analysis(
                services['groq'], 
                clean_context, 
                result, 
                request.analysis_depth,
                extracted_data
            )
            result['suggestion'] = enhanced_analysis
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Determine if ticket is resolved
        status = result.get('status', '').title()
        is_resolved = status in {"Done", "Closed", "Resolved"}
        analysis_type = "resolved_summary" if is_resolved else "unresolved_analysis"
        
        # Extract structured troubleshooting steps
        troubleshooting_steps = _extract_troubleshooting_steps(
            result.get('suggestion', ''), 
            is_resolved,
            extracted_data
        )
        
        # Calculate confidence score based on data quality and references
        confidence_score = _calculate_confidence_score(
            result.get('resolved_reference_count', 0),
            extracted_data,
            len(troubleshooting_steps)
        )

        # Get retrieval method from debug info (use relative import to avoid ModuleNotFoundError)
        from .resolution_assist_service import get_last_assist_debug
        debug_info = get_last_assist_debug()
        retrieval_method = debug_info.get('retrieval_method', 'lexical')

        return JiraAnalyzeResponse(
            ticket_key=request.ticket_key,
            status=status,
            is_resolved=is_resolved,
            analysis_type=analysis_type,
            resolved_reference_count=result.get('resolved_reference_count', 0),
            references=result.get('references', []),
            ai_analysis=result.get('suggestion', ''),
            troubleshooting_steps=troubleshooting_steps,
            confidence_score=round(confidence_score, 2),
            retrieval_method=retrieval_method,
            processing_time=round(processing_time, 3),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log full traceback for deeper debugging while returning sanitized error
        logger.exception(f"JIRA analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _generate_enhanced_analysis(
    groq_client, 
    clean_context: str, 
    base_result: Dict[str, Any], 
    analysis_depth: str,
    extracted_data: Dict[str, str]
) -> str:
    """Generate enhanced analysis using clean ticket context"""
    
    depth_prompts = {
        "quick": "Provide 3-4 immediate diagnostic steps focusing on the most likely causes.",
        "standard": "Provide a thorough analysis with root cause possibilities and step-by-step troubleshooting approach.", 
        "comprehensive": "Provide an in-depth analysis including multiple root cause hypotheses, detailed troubleshooting procedures, and preventive measures."
    }
    
    base_instruction = depth_prompts.get(analysis_depth, depth_prompts["standard"])
    
    # Adjust instruction based on data quality
    data_quality_notes = []
    if not extracted_data['has_analysis']:
        data_quality_notes.append("No existing technical analysis available - provide initial diagnostic approach.")
    if not extracted_data['has_description']:  
        data_quality_notes.append("Limited problem description - focus on information gathering steps first.")
    
    if data_quality_notes:
        base_instruction += f" Note: {' '.join(data_quality_notes)}"
    
    system_prompt = system_prompt_analysis()
    
    # Build context with references
    reference_context = ""
    if base_result.get('references'):
        reference_context = "\n\nSimilar Resolved Tickets:\n"
        for ref in base_result['references'][:3]:  # Top 3 references
            reference_context += f"- {ref.get('ticket_key', 'Unknown')}: {ref.get('summary', 'No summary')}\n"
            if ref.get('l3_engineer_analysis'):
                reference_context += f"  Resolution: {str(ref['l3_engineer_analysis'])[:200]}...\n"
            elif ref.get('l1_l2_analysis'):
                reference_context += f"  Analysis: {str(ref['l1_l2_analysis'])[:200]}...\n"
    
    full_context = clean_context + reference_context
    
    # Centralized analysis user prompt
    query = build_user_prompt_analysis(
        ticket_key=base_result.get('ticket_key','UNKNOWN'),
        ticket_summary=extracted_data.get('summary',''),
        ticket_description=extracted_data.get('description',''),
        reference_summaries=[
            f"{ref.get('ticket_key')}: {ref.get('summary','')[:120]}" for ref in base_result.get('references', [])[:5]
        ]
    )
    
    return await groq_client.generate_response_async(
        query=query,
        context=full_context,
        temperature=0.3,
        max_tokens=800,
        top_p=0.9,
        model=os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile'),
        use_custom_prompt=True,
        custom_system_prompt=system_prompt,
        mode='analyze'
    )

def _extract_troubleshooting_steps(suggestion: str, is_resolved: bool, extracted_data: Dict[str, str]) -> List[str]:
    """Extract structured troubleshooting steps from AI analysis"""
    
    if is_resolved:
        return ["Ticket already resolved - review resolution summary above"]
    
    steps = []
    lines = suggestion.split('\n')
    
    # Look for numbered steps, bullet points, or structured content
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match various step formats
        if (re.match(r'^\d+\.', line) or 
            line.startswith('- ') or 
            line.startswith('• ') or
            line.startswith('Step ') or
            line.startswith('* ') or
            re.match(r'^[A-Z][a-z]+:', line)):  # Action words like "Check:", "Verify:"
            # Clean the step
            cleaned = re.sub(r'^\d+\.\s*', '', line)  # Remove numbering
            cleaned = cleaned.lstrip('•-* ').strip()   # Remove bullets
            if cleaned and len(cleaned) > 5:          # Must be substantial
                steps.append(cleaned)
    
    # If no structured steps found, create basic diagnostic steps
    if not steps:
        steps = _generate_fallback_steps(extracted_data)
    
    return steps[:8]  # Limit to 8 steps for UI

def _generate_fallback_steps(extracted_data: Dict[str, str]) -> List[str]:
    """Generate fallback troubleshooting steps based on available data"""
    
    steps = ["Review ticket details and gather missing information"]
    
    if not extracted_data['has_description']:
        steps.extend([
            "Obtain detailed problem description from reporter", 
            "Collect error messages, logs, and reproduction steps",
            "Verify system environment and configuration details"
        ])
    else:
        steps.extend([
            "Reproduce the issue in a test environment",
            "Check system logs for related error patterns", 
            "Verify configuration against working systems"
        ])
    
    if not extracted_data['has_analysis']:
        steps.append("Perform initial technical analysis and root cause investigation")
    else:
        steps.append("Validate and expand on existing analysis findings")
    
    steps.extend([
        "Search knowledge base for similar resolved issues",
        "Implement and test potential solutions in safe environment", 
        "Document findings and resolution steps for future reference"
    ])
    
    return steps

def _calculate_confidence_score(
    reference_count: int, 
    extracted_data: Dict[str, str], 
    step_count: int
) -> float:
    """Calculate confidence score based on multiple factors"""
    
    score = 0.0
    
    # Base score from reference tickets (0-40%)
    if reference_count >= 3:
        score += 0.4
    elif reference_count >= 2:
        score += 0.3
    elif reference_count >= 1:
        score += 0.2
    else:
        score += 0.05
    
    # Data quality bonus (0-30%)
    if extracted_data['has_description']:
        score += 0.15
    if extracted_data['has_analysis']:
        score += 0.15
    
    # Structured output quality (0-20%) 
    if step_count >= 6:
        score += 0.2
    elif step_count >= 4:
        score += 0.15
    elif step_count >= 2:
        score += 0.1
    
    # Completeness bonus (0-10%)
    if extracted_data['has_description'] and extracted_data['has_analysis'] and reference_count > 0:
        score += 0.1
    
    return min(0.95, score)  # Cap at 95%

@app.get("/api/jira/analyze/debug")
async def get_analyze_debug():
    """Get debug information from the last analysis call"""
    try:
        # Use relative import to match package context
        from .resolution_assist_service import get_last_assist_debug
        debug_info = get_last_assist_debug()
        return {
            "debug_info": debug_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Analysis debug error: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}

# ============================================================================
# Chat Session Management Endpoints
# ============================================================================

@app.post("/api/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(request: ChatSessionRequest):
    """Create a new chat session"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        session_id = await chat_context_service.create_session(
            user_id=request.user_id,
            title=request.title
        )
        
        # Get the created session info
        session_info = await chat_context_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=500, detail="Failed to retrieve created session")
        
        return ChatSessionResponse(**session_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create chat session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions")
async def list_chat_sessions(user_id: str = None, limit: int = 50):
    """List chat sessions for a user"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        sessions = await chat_context_service.list_sessions(user_id=user_id, limit=limit)
        
        return {
            "sessions": sessions,
            "total_count": len(sessions),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"List chat sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get chat session information"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        session_info = await chat_context_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chat session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/sessions/{session_id}", response_model=DeleteResponse)
async def delete_chat_session(session_id: str):
    """Delete a chat session and all its messages"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        success = await chat_context_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete chat session")
        
        return DeleteResponse(
            success=True,
            message=f"Chat session {session_id} deleted successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete chat session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        messages = await chat_context_service.get_chat_history(session_id, limit=limit)
        
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/messages/{message_id}", response_model=DeleteResponse)
async def delete_chat_message(message_id: str):
    """Delete a specific chat message"""
    try:
        chat_context_service = services.get('chat_context')
        if not chat_context_service:
            raise HTTPException(status_code=503, detail="Chat context service not available")
        
        success = await chat_context_service.delete_message(message_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Message not found or failed to delete")
        
        return DeleteResponse(
            success=True,
            message=f"Message {message_id} deleted successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete chat message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_langgraph:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
