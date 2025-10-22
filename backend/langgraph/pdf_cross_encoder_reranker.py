"""
Local Cross-Encoder Reranking Service for PDF Processing
========================================================

Based on the existing rerank_service_local.py implementation
Uses cross-encoder/ms-marco-MiniLM-L6-v2 for better retrieval results
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import time

logger = logging.getLogger(__name__)

class LocalCrossEncoderReranker:
    """Local reranking service using cross-encoder/ms-marco-MiniLM-L6-v2"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.is_initialized = False
        
        logger.info(f"Initializing Cross-Encoder Reranker with model: {model_name}")
        logger.info(f"Using device: {self.device}")
    
    async def initialize(self):
        """Initialize the model and tokenizer"""
        if self.is_initialized:
            return
            
        try:
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._load_model)
            self.is_initialized = True
            logger.info("Cross-encoder reranker service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cross-encoder reranker: {e}")
            raise
    
    def _load_model(self):
        """Load model and tokenizer (runs in thread pool)"""
        try:
            logger.info("Loading cross-encoder tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            logger.info("Loading cross-encoder model...")
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"Cross-encoder model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Error loading cross-encoder model: {e}")
            raise
    
    def _rerank_batch(self, query: str, documents: List[str]) -> List[float]:
        """Perform reranking on a batch of documents (runs in thread pool)"""
        try:
            # Prepare input pairs
            pairs = [[query, doc] for doc in documents]
            
            # Tokenize
            features = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512
            )
            
            # Move to device
            features = {k: v.to(self.device) for k, v in features.items()}
            
            # Get predictions
            with torch.no_grad():
                scores = self.model(**features).logits
                
            # Convert to relevance scores (apply sigmoid for probability)
            relevance_scores = torch.sigmoid(scores).squeeze().cpu().numpy()
            
            # Ensure we return a list even for single item
            if len(documents) == 1:
                relevance_scores = [float(relevance_scores)]
            else:
                relevance_scores = relevance_scores.tolist()
            
            return relevance_scores
            
        except Exception as e:
            logger.error(f"Error in cross-encoder reranking batch: {e}")
            # Return neutral scores as fallback
            return [0.5] * len(documents)
    
    async def rerank_documents_async(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        batch_size: int = 32,
        score_threshold: float = 0.0,
        adaptive_threshold: bool = True,
        adaptive_ratio: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using the cross-encoder model
        
        Args:
            query: Search query
            documents: List of document dictionaries with 'text' or 'content' field
            top_k: Number of top documents to return
            batch_size: Batch size for processing (for memory management)
            score_threshold: Minimum score threshold for filtering (used as fallback)
            adaptive_threshold: Whether to use adaptive threshold based on top score
            adaptive_ratio: Ratio of top score to use as adaptive threshold (0.6 = 60% of top score)
            
        Returns:
            List of reranked documents with cross-encoder scores
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not documents:
            return []
        
        start_time = time.time()
        
        try:
            # Extract content from documents
            doc_contents = []
            for doc in documents:
                if isinstance(doc, dict):
                    # Try different field names for content
                    content = (doc.get('text', '') or 
                              doc.get('content', '') or 
                              doc.get('chunk_text', '') or 
                              str(doc))
                else:
                    content = str(doc)
                doc_contents.append(content)
            
            # Process in batches if needed
            all_scores = []
            
            for i in range(0, len(doc_contents), batch_size):
                batch_docs = doc_contents[i:i + batch_size]
                
                # Run reranking in thread pool
                loop = asyncio.get_event_loop()
                batch_scores = await loop.run_in_executor(
                    self.executor, 
                    self._rerank_batch, 
                    query, 
                    batch_docs
                )
                all_scores.extend(batch_scores)
            
            # Combine documents with scores
            scored_docs = []
            for doc, score in zip(documents, all_scores):
                scored_doc = doc.copy() if isinstance(doc, dict) else {'content': str(doc)}
                scored_doc['rerank_score'] = float(score)
                scored_doc['cross_encoder_score'] = float(score)  # Alternative field name
                scored_docs.append(scored_doc)
            
            # Sort by score (descending)
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Apply adaptive or fixed threshold filter
            filtered_docs = scored_docs
            threshold_used = score_threshold
            
            if adaptive_threshold and scored_docs:
                # Use adaptive threshold based on top score
                top_score = scored_docs[0]['rerank_score']
                adaptive_threshold_value = top_score * adaptive_ratio
                
                # Use the higher of adaptive threshold or minimum score_threshold
                threshold_used = max(adaptive_threshold_value, score_threshold)
                
                filtered_docs = [doc for doc in scored_docs if doc['rerank_score'] >= threshold_used]
                
                logger.info(f"Cross-encoder adaptive threshold: top_score={top_score:.4f}, "
                           f"adaptive_threshold={adaptive_threshold_value:.4f} "
                           f"(ratio={adaptive_ratio}), used_threshold={threshold_used:.4f}")
                logger.info(f"Applied adaptive threshold {threshold_used:.4f}: {len(filtered_docs)} docs remaining")
                
            elif score_threshold > 0:
                # Use fixed threshold
                filtered_docs = [doc for doc in scored_docs if doc['rerank_score'] >= score_threshold]
                logger.info(f"Applied fixed threshold {score_threshold}: {len(filtered_docs)} docs remaining")
            
            # Return top_k from filtered results
            result = filtered_docs[:top_k]
            
            elapsed = time.time() - start_time
            
            # Log score distribution for debugging
            if scored_docs:
                scores = [doc['rerank_score'] for doc in scored_docs]
                min_score, max_score = min(scores), max(scores)
                avg_score = sum(scores) / len(scores)
                
                logger.info(f"Cross-encoder reranking completed in {elapsed:.2f}s")
                logger.info(f"Score distribution: min={min_score:.4f}, max={max_score:.4f}, avg={avg_score:.4f}")
                logger.info(f"Returning {len(result)} documents (from {len(documents)} input docs)")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error in cross-encoder reranking after {elapsed:.2f}s: {e}")
            # Return original documents as fallback
            return documents[:top_k]
    
    def rerank_documents_sync(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Synchronous reranking method for backward compatibility
        
        Args:
            query: Search query
            documents: List of document dictionaries
            top_k: Number of top documents to return
            
        Returns:
            List of reranked documents
        """
        try:
            # Simple synchronous implementation
            if not self.is_initialized:
                # Initialize synchronously (blocking)
                self._load_model()
                self.is_initialized = True
            
            # Extract content
            doc_contents = []
            for doc in documents:
                if isinstance(doc, dict):
                    content = (doc.get('text', '') or 
                              doc.get('content', '') or 
                              doc.get('chunk_text', '') or 
                              str(doc))
                else:
                    content = str(doc)
                doc_contents.append(content)
            
            # Get scores
            scores = self._rerank_batch(query, doc_contents)
            
            # Combine and sort
            scored_docs = []
            for doc, score in zip(documents, scores):
                scored_doc = doc.copy() if isinstance(doc, dict) else {'content': str(doc)}
                scored_doc['rerank_score'] = float(score)
                scored_doc['cross_encoder_score'] = float(score)
                scored_docs.append(scored_doc)
            
            # Sort and return top_k
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error in synchronous cross-encoder reranking: {e}")
            return documents[:top_k]
    
    def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache() if torch.cuda.is_available() else None


# Factory function to create reranker instance
def create_cross_encoder_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2") -> LocalCrossEncoderReranker:
    """
    Create a cross-encoder reranker instance
    
    Args:
        model_name: HuggingFace model name for cross-encoder
        
    Returns:
        LocalCrossEncoderReranker instance
    """
    return LocalCrossEncoderReranker(model_name)