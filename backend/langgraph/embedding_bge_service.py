"""
BGE Embedding Service
=====================

Provides embeddings using BAAI/bge-large-en-v1.5 (SentenceTransformers).
Supports:
- Local snapshot directory via LOCAL_EMBEDDING_MODEL_DIR
- Normalization (cosine-friendly)
- Batch & single encode interfaces matching previous internal embedding API

Environment Variables:
  LOCAL_EMBEDDING_MODEL_DIR: Absolute path to a local model snapshot (optional)
  EMBEDDING_MODEL_NAME: Override model name (default BAAI/bge-large-en-v1.5)
"""
from __future__ import annotations
import os
import logging
from typing import List, Sequence, Optional
import math
import asyncio

try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers") from e

logger = logging.getLogger(__name__)

class BGEEmbeddingService:
    def __init__(self, model_name: str | None = None, local_dir: str | None = None, normalize: bool = True):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-large-en-v1.5")
        self.local_dir = local_dir or os.getenv("LOCAL_EMBEDDING_MODEL_DIR")
        self.normalize = normalize
        self.model = self._load()
        try:
            self._dimension = self.model.get_sentence_embedding_dimension()
        except Exception:
            # Fallback dimension check (encode a token)
            test_vec = self.model.encode(["dimension probe"], normalize_embeddings=self.normalize)
            self._dimension = len(test_vec[0])
        logger.info(f"✅ Loaded BGE model '{self.model_name}' (dim={self._dimension})" + (f" from local dir {self.local_dir}" if self.local_dir else ""))
        # Tune batch size based on device & env override
        self._device = getattr(self.model, 'device', 'cpu')
        env_batch = os.getenv('EMBEDDING_BATCH_SIZE')
        if env_batch and env_batch.isdigit():
            self._batch_size = int(env_batch)
        else:
            # Heuristic: smaller on CPU
            self._batch_size = 32 if 'cuda' in str(self._device) else 16
        logger.info(f"BGEEmbeddingService using batch_size={self._batch_size} device={self._device}")

    def _load(self):
        load_path = self.local_dir if self.local_dir else self.model_name
        logger.info(f"Loading BGE embedding model from: {load_path}")
        model = SentenceTransformer(load_path, trust_remote_code=True)
        return model

    def get_embedding(self, text: str) -> List[float]:
        if not isinstance(text, str):
            text = str(text)
        vec = self.model.encode([text], normalize_embeddings=self.normalize)[0]
        return vec.tolist()

    def get_embeddings(self, texts: Sequence[str]) -> List[List[float]]:
        texts = [t if isinstance(t, str) else str(t) for t in texts]
        vectors = self.model.encode(texts, normalize_embeddings=self.normalize)
        return [v.tolist() for v in vectors]

    async def get_embeddings_batch_async(self, texts: Sequence[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """Asynchronous batch embedding to mirror Gemma interface.

        Splits texts into batches, runs encode synchronously in executor to avoid blocking event loop.
        """
        if batch_size is None:
            batch_size = self._batch_size
        loop = asyncio.get_event_loop()
        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            # Execute encode in thread pool (provide kwargs via lambda to avoid arg misinterpretation)
            vecs = await loop.run_in_executor(None, lambda b=batch: self.model.encode(b, normalize_embeddings=self.normalize))
            results.extend(v.tolist() for v in vecs)
        return results

    def get_dimension(self) -> int:
        return self._dimension


def create_bge_embedding_service() -> BGEEmbeddingService:
    return BGEEmbeddingService()

if __name__ == "__main__":
    svc = create_bge_embedding_service()
    emb = svc.get_embedding("BGE quick sanity test")
    print("Model:", svc.model_name)
    print("Dim:", len(emb))
    print("First 6 dims:", emb[:6])
