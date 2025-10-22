"""
LangGraph State Schema for Dual Document Processing
==================================================

Defines the state structure for the LangGraph workflow that processes
both PDF documents and JIRA tickets with different logic.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from datetime import datetime

# Document types
DocumentType = Literal["pdf", "jira"]
ProcessingStage = Literal["routing", "extraction", "chunking", "embedding", "reranking", "storage", "completed", "error"]

@dataclass
class DocumentInfo:
    """Information about a document being processed"""
    file_path: str
    document_type: DocumentType
    file_name: str
    file_size: int
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ChunkInfo:
    """Information about a processed chunk"""
    chunk_id: str
    text: str
    chunk_index: int
    chunk_type: str  # paragraph_group, sentence_group, complete
    page_number: Optional[int] = None
    ticket_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class EmbeddingInfo:
    """Information about generated embeddings"""
    chunk_id: str
    embedding: List[float]
    model_name: str
    dimension: int

@dataclass
class SearchResult:
    """Search result with reranking scores"""
    chunk_id: str
    similarity_score: float
    chunk_text: str
    rerank_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentProcessingState(TypedDict):
    """
    Complete state for the LangGraph dual document processing workflow
    """
    # Input configuration
    pdf_directory: str
    jira_directory: str
    collection_name_pdf: str
    collection_name_jira: str
    
    # Current processing context
    current_stage: ProcessingStage
    current_document: Optional[DocumentInfo]
    processing_batch: List[DocumentInfo]
    
    # Processing results
    extracted_pages: List[Dict[str, Any]]  # For PDFs
    extracted_tickets: List[Dict[str, Any]]  # For JIRA
    generated_chunks: List[ChunkInfo]
    generated_embeddings: List[EmbeddingInfo]
    
    # Search and retrieval
    search_query: Optional[str]
    search_results: List[SearchResult]
    reranked_results: List[SearchResult]
    
    # Processing statistics
    stats: Dict[str, Any]
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    
    # Configuration
    config: Dict[str, Any]
    
    # Services (references to initialized services)
    services: Dict[str, Any]