"""
LangGraph Nodes for Dual Document Processing
============================================

Implements the individual nodes for the LangGraph workflow:
- Document routing
- PDF processing 
- JIRA processing
- Embedding generation
- Cross-encoder reranking
- Vector storage
- Search and retrieval
"""

import logging
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

from .langgraph_state_schema import (
    DocumentProcessingState, 
    DocumentInfo, 
    ChunkInfo, 
    EmbeddingInfo,
    SearchResult,
    DocumentType
)

# Import our existing services
from .pdf_processor import PDFProcessor
from .jira_document_processor import JIRATicketProcessor  
from .embedding_bge_service import create_bge_embedding_service
from .jira_qdrant_service import JiraQdrantService
from .pdf_cross_encoder_reranker import create_cross_encoder_reranker

logger = logging.getLogger(__name__)

class DocumentProcessingNodes:
    """LangGraph nodes for dual document processing workflow"""
    
    def __init__(self):
        """Initialize services for the nodes"""
        self.embedding_service = None
        self.qdrant_service = None
        self.pdf_processor = None
        self.jira_processor = None
        self.reranker = None
        
    async def initialize_services(self) -> Dict[str, Any]:
        """Initialize all services and return them"""
        logger.info("🔧 Initializing services for LangGraph workflow...")
        
        # Initialize services
        self.embedding_service = create_bge_embedding_service()
        self.qdrant_service = JiraQdrantService()
        self.reranker = create_cross_encoder_reranker()
        
        # Initialize reranker
        await self.reranker.initialize()
        
        # Create processors with services
        self.pdf_processor = PDFProcessor(
            embedding_service=self.embedding_service,
            qdrant_service=self.qdrant_service
        )
        
        self.jira_processor = JIRATicketProcessor(
            embedding_service=self.embedding_service,
            qdrant_service=self.qdrant_service
        )
        
        services = {
            "embedding_service": self.embedding_service,
            "qdrant_service": self.qdrant_service,
            "pdf_processor": self.pdf_processor,
            "jira_processor": self.jira_processor,
            "reranker": self.reranker
        }
        
        logger.info("✅ All services initialized for LangGraph")
        return services

    def route_documents_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Node: Route documents based on type and location
        """
        logger.info("📍 LangGraph Node: Document Routing")
        
        state["current_stage"] = "routing"
        processing_batch = []
        
        # Scan PDF directory
        pdf_path = Path(state["pdf_directory"])
        if pdf_path.exists():
            for pdf_file in pdf_path.glob("*.pdf"):
                doc_info = DocumentInfo(
                    file_path=str(pdf_file),
                    document_type="pdf",
                    file_name=pdf_file.name,
                    file_size=pdf_file.stat().st_size,
                    created_at=datetime.fromtimestamp(pdf_file.stat().st_ctime),
                    metadata={"source_directory": str(pdf_path)}
                )
                processing_batch.append(doc_info)
        
        # Scan JIRA directory
        jira_path = Path(state["jira_directory"])
        if jira_path.exists():
            # Look for both .txt and .json files for JIRA tickets
            for pattern in ["*.txt", "*.json"]:
                for jira_file in jira_path.glob(pattern):
                    doc_info = DocumentInfo(
                        file_path=str(jira_file),
                        document_type="jira", 
                        file_name=jira_file.name,
                        file_size=jira_file.stat().st_size,
                        created_at=datetime.fromtimestamp(jira_file.stat().st_ctime),
                        metadata={"source_directory": str(jira_path)}
                    )
                    processing_batch.append(doc_info)
        
        state["processing_batch"] = processing_batch
        
        logger.info(f"📍 Routed {len(processing_batch)} documents:")
        pdf_count = len([d for d in processing_batch if d.document_type == "pdf"])
        jira_count = len([d for d in processing_batch if d.document_type == "jira"])
        logger.info(f"   📄 PDF documents: {pdf_count}")
        logger.info(f"   🎫 JIRA documents: {jira_count}")
        
        return state

    async def process_pdf_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Node: Process PDF documents with intelligent chunking
        """
        logger.info("📄 LangGraph Node: PDF Processing")
        
        state["current_stage"] = "extraction"
        pdf_processor = state["services"]["pdf_processor"]
        
        pdf_documents = [doc for doc in state["processing_batch"] if doc.document_type == "pdf"]
        
        if not pdf_documents:
            logger.info("No PDF documents to process")
            return state
            
        all_chunks = []
        
        for doc in pdf_documents:
            try:
                logger.info(f"Processing PDF: {doc.file_name}")
                state["current_document"] = doc
                
                # Extract and create chunks using existing enhanced processor
                pdf_chunks = await pdf_processor._run_in_executor(
                    pdf_processor.create_pdf_chunks, 
                    doc.file_path
                )
                
                # Convert to ChunkInfo objects
                for chunk in pdf_chunks:
                    chunk_info = ChunkInfo(
                        chunk_id=chunk.metadata["chunk_id"],
                        text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        chunk_type=chunk.metadata.get("chunk_type", "standard"),
                        page_number=chunk.page_number,
                        metadata=chunk.metadata
                    )
                    all_chunks.append(chunk_info)
                    
                logger.info(f"✅ PDF processed: {len(pdf_chunks)} chunks created")
                
            except Exception as e:
                error_msg = f"Error processing PDF {doc.file_name}: {e}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
        
        state["generated_chunks"].extend(all_chunks)
        
        logger.info(f"📄 PDF Processing Complete: {len(all_chunks)} total chunks")
        return state

    async def process_jira_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Node: Process JIRA tickets with metadata extraction
        """
        logger.info("🎫 LangGraph Node: JIRA Processing")
        
        state["current_stage"] = "extraction"
        jira_processor = state["services"]["jira_processor"]
        
        jira_documents = [doc for doc in state["processing_batch"] if doc.document_type == "jira"]
        
        if not jira_documents:
            logger.info("No JIRA documents to process")
            return state
            
        all_chunks = []
        
        for doc in jira_documents:
            try:
                logger.info(f"Processing JIRA: {doc.file_name}")
                state["current_document"] = doc
                
                # Parse JIRA tickets from file
                tickets = jira_processor.parse_ticket_file(doc.file_path)
                
                # Process each ticket individually
                for ticket in tickets:
                    ticket_chunks = jira_processor.create_ticket_chunks(ticket)
                    
                    # Convert to ChunkInfo objects
                    for chunk in ticket_chunks:
                        chunk_info = ChunkInfo(
                            chunk_id=chunk.chunk_id,
                            text=chunk.text,
                            chunk_index=chunk.chunk_index,
                            chunk_type="ticket",
                            ticket_id=chunk.ticket_id,
                            metadata=chunk.metadata
                        )
                        all_chunks.append(chunk_info)
                    
                logger.info(f"✅ JIRA processed: {len(ticket_chunks)} chunks created")
                
            except Exception as e:
                error_msg = f"Error processing JIRA {doc.file_name}: {e}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
        
        state["generated_chunks"].extend(all_chunks)
        
        logger.info(f"🎫 JIRA Processing Complete: {len(all_chunks)} total chunks")
        return state

    async def generate_embeddings_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
    Node: Generate embeddings using BGE (1024-d)
        """
        logger.info("🧠 LangGraph Node: Embedding Generation")
        
        state["current_stage"] = "embedding"
        embedding_service = state["services"]["embedding_service"]
        
        chunks = state["generated_chunks"]
        if not chunks:
            logger.warning("No chunks found for embedding generation")
            return state
            
        # Extract texts for batch processing
        texts = [chunk.text for chunk in chunks]
        
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        
        # Generate embeddings in batches
        batch_size = state["config"].get("embedding_batch_size", 64)
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_end = min(i + batch_size, len(texts))
            batch_texts = texts[i:batch_end]
            
            # Generate embeddings for batch
            batch_embeddings = await embedding_service.get_embeddings_batch_async(batch_texts)
            
            # Create EmbeddingInfo objects
            for j, embedding in enumerate(batch_embeddings):
                chunk_idx = i + j
                chunk = chunks[chunk_idx]
                
                embedding_info = EmbeddingInfo(
                    chunk_id=chunk.chunk_id,
                    embedding=embedding,
                    model_name=embedding_service.model_name,
                    dimension=len(embedding)
                )
                all_embeddings.append(embedding_info)
            
            logger.info(f"Generated embeddings for batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            await asyncio.sleep(0.01)  # Yield control
        
        state["generated_embeddings"] = all_embeddings
        
        logger.info(f"🧠 Embedding Generation Complete: {len(all_embeddings)} embeddings")
        return state

    async def rerank_results_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Node: Rerank search results using cross-encoder
        """
        logger.info("🎯 LangGraph Node: Cross-Encoder Reranking")
        
        state["current_stage"] = "reranking"
        reranker = state["services"]["reranker"]
        
        search_results = state.get("search_results", [])
        search_query = state.get("search_query")
        
        if not search_results or not search_query:
            logger.warning("No search results or query for reranking")
            state["reranked_results"] = search_results
            return state
        
        # Prepare documents for reranking
        documents = []
        for result in search_results:
            documents.append({
                "text": result.chunk_text,
                "chunk_id": result.chunk_id,
                "similarity_score": result.similarity_score,
                "metadata": result.metadata
            })
        
        # Apply cross-encoder reranking
        reranked_docs = await reranker.rerank_documents_async(
            query=search_query,
            documents=documents,
            top_k=state["config"].get("rerank_top_k", 10),
            adaptive_threshold=True,
            adaptive_ratio=0.6
        )
        
        # Convert back to SearchResult objects
        reranked_results = []
        for doc in reranked_docs:
            result = SearchResult(
                chunk_id=doc["chunk_id"],
                similarity_score=doc.get("similarity_score", 0.0),
                rerank_score=doc.get("rerank_score", 0.0),
                chunk_text=doc["text"],
                metadata=doc.get("metadata", {})
            )
            reranked_results.append(result)
        
        state["reranked_results"] = reranked_results
        
        logger.info(f"🎯 Reranking Complete: {len(reranked_results)} results")
        return state

    async def store_vectors_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Node: Store vectors in Qdrant database
        """
        logger.info("🗄️ LangGraph Node: Vector Storage")
        
        state["current_stage"] = "storage"
        qdrant_service = state["services"]["qdrant_service"]
        
        chunks = state["generated_chunks"]
        embeddings = state["generated_embeddings"]
        
        if len(chunks) != len(embeddings):
            error_msg = f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state
        
        # Group by document type for different collections
        pdf_docs = []
        jira_docs = []
        
        for chunk, embedding in zip(chunks, embeddings):
            doc_data = {
                "id": chunk.chunk_id,
                "vector": embedding.embedding,
                "payload": {
                    "text": chunk.text,
                    "chunk_id": chunk.chunk_id,
                    "chunk_type": chunk.chunk_type,
                    "collection_name": state["collection_name_jira"] if chunk.page_number is None else state["collection_name_pdf"],
                    **(chunk.metadata or {})
                }
            }
            
            if chunk.page_number is not None:  # PDF document
                doc_data["payload"]["collection_name"] = state["collection_name_pdf"]
                pdf_docs.append(doc_data)
            else:  # JIRA document
                doc_data["payload"]["collection_name"] = state["collection_name_jira"]
                jira_docs.append(doc_data)
        
        # Get vector dimension from first embedding or embedding service
        if embeddings:
            # Try to get dimension from embedding object or vector length
            if hasattr(embeddings[0], 'dimension'):
                vector_size = embeddings[0].dimension
            elif hasattr(embeddings[0], 'vector') and embeddings[0].vector:
                vector_size = len(embeddings[0].vector)
            else:
                vector_size = 1024  # Default BGE dimension
        else:
            # Get dimension from embedding service
            from embedding_service_factory import create_embedding_backend
            embedding_service = create_embedding_backend()
            vector_size = embedding_service.get_dimension()
            logger.info(f"🔍 Using embedding service dimension: {vector_size}")
        
        # Store PDF documents
        if pdf_docs:
            await qdrant_service.ensure_collection_exists_async(
                collection_name=state["collection_name_pdf"],
                vector_size=vector_size
            )
            pdf_ids = await qdrant_service.add_documents_batch_async(pdf_docs)
            pdf_count = len(pdf_ids) if pdf_ids else len(pdf_docs)
            logger.info(f"Stored {pdf_count} PDF vectors in {state['collection_name_pdf']}")
        
        # Store JIRA documents  
        if jira_docs:
            await qdrant_service.ensure_collection_exists_async(
                collection_name=state["collection_name_jira"],
                vector_size=vector_size
            )
            jira_ids = await qdrant_service.add_documents_batch_async(jira_docs)
            jira_count = len(jira_ids) if jira_ids else len(jira_docs)
            logger.info(f"Stored {jira_count} JIRA vectors in {state['collection_name_jira']}")
        
        # Update statistics
        state["stats"]["vectors_stored"] = len(embeddings)
        state["stats"]["pdf_vectors"] = len(pdf_docs)
        state["stats"]["jira_vectors"] = len(jira_docs)
        
        logger.info(f"🗄️ Vector Storage Complete: {len(embeddings)} vectors stored")
        return state

    def should_process_pdfs(self, state: DocumentProcessingState) -> str:
        """Routing function: Check if we should process PDFs"""
        pdf_docs = [doc for doc in state["processing_batch"] if doc.document_type == "pdf"]
        return "process_pdf" if pdf_docs else "process_jira"
        
    def should_process_jiras(self, state: DocumentProcessingState) -> str:
        """Routing function: Check if we should process JIRAs"""  
        jira_docs = [doc for doc in state["processing_batch"] if doc.document_type == "jira"]
        return "process_jira" if jira_docs else "generate_embeddings"