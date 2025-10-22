"""Ticket Cross-Encoder Reranker Service
Adapts the old backend LocalHuggingFaceRerankerService for ticket semantic reranking.
Lightweight wrapper with async API and graceful fallbacks.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import time

try:
    import torch  # type: ignore
    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    AutoTokenizer = None  # type: ignore
    AutoModelForSequenceClassification = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"

class TicketCrossEncoderReranker:
    def __init__(self, model_name: str = DEFAULT_RERANK_MODEL, max_workers: int = 2):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.is_initialized = False
        self._init_error: Optional[str] = None

    async def initialize(self):
        if self.is_initialized or self._init_error:
            return
        if torch is None or AutoTokenizer is None:
            self._init_error = "transformers/torch not available"
            logger.warning("Reranker unavailable: transformers/torch not installed")
            return
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._load_model)
            self.is_initialized = True
            logger.info(f"Ticket reranker initialized: {self.model_name} on {self.device}")
        except Exception as e:  # pragma: no cover
            self._init_error = str(e)
            logger.error(f"Ticket reranker init failed: {e}")

    def _load_model(self):
        self.device = torch.device("cuda" if torch and torch.cuda.is_available() else "cpu")
        logger.info(f"Loading reranker tokenizer {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        logger.info("Loading reranker model ...")
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

    def _batch_scores(self, query: str, docs: List[str]):
        try:
            pairs = [[query, d] for d in docs]
            tokens = self.tokenizer(pairs, padding=True, truncation=True, max_length=256, return_tensors="pt")
            tokens = {k: v.to(self.device) for k,v in tokens.items()}
            with torch.no_grad():
                logits = self.model(**tokens).logits
            scores = torch.sigmoid(logits).squeeze().cpu().numpy()
            if scores.ndim == 0:
                scores = [float(scores)]
            else:
                scores = scores.tolist()
            return [float(s) for s in scores]
        except Exception as e:  # pragma: no cover
            logger.warning(f"Reranker batch scoring failed: {e}")
            return [0.5]*len(docs)

    async def rerank_async(self, query: str, candidates: List[Dict[str, Any]], content_field: str = "chunk_text", top_k: int = 8) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        await self.initialize()
        if not self.is_initialized:
            return candidates[:top_k]
        # Build documents text (summary + snippet)
        docs = []
        for c in candidates:
            summary = c.get('summary') or c.get('payload', {}).get('summary') or ''
            snippet = c.get(content_field) or c.get('chunk_text') or c.get('text') or ''
            docs.append(f"{summary}\n{snippet[:400]}")
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(self.executor, self._batch_scores, query, docs)
        # Attach scores and sort
        enriched = []
        for c, s in zip(candidates, scores):
            c2 = dict(c)
            c2['rerank_score'] = s
            enriched.append(c2)
        enriched.sort(key=lambda x: x['rerank_score'], reverse=True)
        logger.info("TicketReranker: top scores=" + ", ".join(f"{e.get('ticket_key')}:{e['rerank_score']:.3f}" for e in enriched[:min(5,len(enriched))]))
        return enriched[:top_k]

    async def health(self) -> Dict[str, Any]:
        return {
            "initialized": self.is_initialized,
            "model": self.model_name,
            "error": self._init_error,
        }

# Convenience global (lazy init)
ticket_reranker_service = TicketCrossEncoderReranker()
