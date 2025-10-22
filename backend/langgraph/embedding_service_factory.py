"""Embedding Service Factory (BGE Only)

Central factory for creating the active embedding backend.

Currently standardized on BGE (BAAI/bge-large-en-v1.5). Legacy Gemma code removed.

Environment Variables:
  EMBEDDING_MODEL_NAME: Override model id (default BAAI/bge-large-en-v1.5)
  LOCAL_EMBEDDING_MODEL_DIR: Optional local snapshot path
  EMBEDDING_BATCH_SIZE: Batch size override for encoding
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

def create_embedding_backend():
    from .embedding_bge_service import create_bge_embedding_service
    svc = create_bge_embedding_service()
    logger.info(f"Embedding factory: BGE backend active model='{svc.model_name}' dim={svc.get_dimension()}")
    return svc

__all__ = ["create_embedding_backend"]