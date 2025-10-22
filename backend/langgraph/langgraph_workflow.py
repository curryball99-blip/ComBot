"""
LangGraph Dual Document Processing Workflow
===========================================

Implements the complete LangGraph StateGraph for processing both PDF documents 
and JIRA tickets with different logic, using BGE embeddings (BAAI/bge-large-en-v1.5, 1024-d) and cross-encoder reranking.

The workflow:
1. Route documents by type (PDF vs JIRA)
2. Process PDFs with intelligent chunking  
3. Process JIRA tickets with metadata extraction
4. Generate embeddings using BGE (1024-d)
5. Store vectors in separate Qdrant collections
6. Support search with cross-encoder reranking
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from .langgraph_state_schema import DocumentProcessingState
from .langgraph_nodes import DocumentProcessingNodes

logger = logging.getLogger(__name__)

class DualDocumentProcessingWorkflow:
    """
    LangGraph-based dual document processing workflow
    """
    
    def __init__(self, 
                 pdf_directory: str = "/home/ubuntu/Ravi/ComBot/uploads/",
                 jira_directory: str = "/home/ubuntu/Ravi/ComBot/backend/documents/",
                 collection_name_pdf: str = "pdf_documents",
                 collection_name_jira: str = "jira_tickets"):
        """
        Initialize the LangGraph workflow
        
        Args:
            pdf_directory: Directory containing PDF files
            jira_directory: Directory containing JIRA ticket files  
            collection_name_pdf: Qdrant collection for PDF documents
            collection_name_jira: Qdrant collection for JIRA tickets
        """
        self.pdf_directory = pdf_directory
        self.jira_directory = jira_directory
        self.collection_name_pdf = collection_name_pdf
        self.collection_name_jira = collection_name_jira
        
        # Initialize nodes
        self.nodes = DocumentProcessingNodes()
        
        # Build the graph
        self.graph = None
        self.compiled_graph = None
        
    async def initialize(self):
        """Initialize services and build the graph"""
        logger.info("🔧 Initializing LangGraph Dual Document Processing Workflow...")
        
        # Initialize services
        services = await self.nodes.initialize_services()
        
        # Build the StateGraph
        await self._build_graph(services)
        
        logger.info("✅ LangGraph workflow initialized and ready!")
    
    async def _build_graph(self, services: Dict[str, Any]):
        """Build the LangGraph StateGraph"""
        logger.info("🏗️ Building LangGraph StateGraph...")
        
        # Create the StateGraph
        workflow = StateGraph(DocumentProcessingState)
        
        # Add nodes
        workflow.add_node("route_documents", self.nodes.route_documents_node)
        workflow.add_node("process_pdf", self.nodes.process_pdf_node)
        workflow.add_node("process_jira", self.nodes.process_jira_node)  
        workflow.add_node("generate_embeddings", self.nodes.generate_embeddings_node)
        workflow.add_node("store_vectors", self.nodes.store_vectors_node)
        workflow.add_node("rerank_results", self.nodes.rerank_results_node)
        
        # Define the workflow edges
        workflow.add_edge(START, "route_documents")
        
        # Conditional routing after document routing
        workflow.add_conditional_edges(
            "route_documents",
            self._routing_logic,
            {
                "process_both": "process_pdf",
                "process_pdf_only": "process_pdf", 
                "process_jira_only": "process_jira",
                "no_documents": END
            }
        )
        
        # PDF processing flow
        workflow.add_conditional_edges(
            "process_pdf",
            self._after_pdf_logic,
            {
                "process_jira": "process_jira",
                "generate_embeddings": "generate_embeddings"
            }
        )
        
        # JIRA processing flow
        workflow.add_edge("process_jira", "generate_embeddings")
        
        # Embedding and storage flow
        workflow.add_edge("generate_embeddings", "store_vectors")
        workflow.add_edge("store_vectors", END)
        
        # Reranking flow (separate path for search)
        workflow.add_edge("rerank_results", END)
        
        # Compile the graph
        self.graph = workflow
        self.compiled_graph = workflow.compile()
        
        logger.info("✅ LangGraph StateGraph built successfully!")
        
    def _routing_logic(self, state: DocumentProcessingState) -> str:
        """Determine initial routing logic"""
        processing_batch = state.get("processing_batch", [])
        
        if not processing_batch:
            return "no_documents"
            
        has_pdf = any(doc.document_type == "pdf" for doc in processing_batch)
        has_jira = any(doc.document_type == "jira" for doc in processing_batch)
        
        if has_pdf and has_jira:
            return "process_both"
        elif has_pdf:
            return "process_pdf_only"
        elif has_jira:
            return "process_jira_only"
        else:
            return "no_documents"
    
    def _after_pdf_logic(self, state: DocumentProcessingState) -> str:
        """Logic after PDF processing"""
        processing_batch = state.get("processing_batch", [])
        has_jira = any(doc.document_type == "jira" for doc in processing_batch)
        
        return "process_jira" if has_jira else "generate_embeddings"
    
    def _create_initial_state(self, **kwargs) -> DocumentProcessingState:
        """Create initial state for the workflow"""
        return {
            # Configuration
            "pdf_directory": self.pdf_directory,
            "jira_directory": self.jira_directory,
            "collection_name_pdf": self.collection_name_pdf,
            "collection_name_jira": self.collection_name_jira,
            
            # Processing state
            "current_stage": "routing",
            "current_document": None,
            "processing_batch": [],
            
            # Results
            "extracted_pages": [],
            "extracted_tickets": [],
            "generated_chunks": [],
            "generated_embeddings": [],
            
            # Search
            "search_query": kwargs.get("search_query"),
            "search_results": [],
            "reranked_results": [],
            
            # Statistics
            "stats": {
                "start_time": datetime.now().isoformat(),
                "documents_processed": 0,
                "chunks_created": 0,
                "embeddings_generated": 0,
                "vectors_stored": 0,
                "pdf_vectors": 0,
                "jira_vectors": 0
            },
            
            # Error handling
            "errors": [],
            "warnings": [],
            
            # Configuration
            "config": {
                "embedding_batch_size": 64,
                "rerank_top_k": 10,
                "enable_reranking": True,
                **kwargs.get("config", {})
            },
            
            # Services
            "services": {}
        }
    
    async def process_documents(self, **kwargs) -> DocumentProcessingState:
        """
        Process all documents using the LangGraph workflow
        
        Args:
            **kwargs: Additional configuration options
            
        Returns:
            Final state with processing results
        """
        if not self.compiled_graph:
            await self.initialize()
        
        logger.info("🚀 Starting LangGraph dual document processing...")
        
        # Create initial state
        initial_state = self._create_initial_state(**kwargs)
        initial_state["services"] = {
            "embedding_service": self.nodes.embedding_service,
            "qdrant_service": self.nodes.qdrant_service,
            "pdf_processor": self.nodes.pdf_processor,
            "jira_processor": self.nodes.jira_processor,
            "reranker": self.nodes.reranker
        }
        
        # Execute the workflow
        try:
            final_state = await self.compiled_graph.ainvoke(initial_state)
            
            # Update final statistics
            final_state["stats"]["end_time"] = datetime.now().isoformat()
            final_state["stats"]["documents_processed"] = len(final_state.get("processing_batch", []))
            final_state["stats"]["chunks_created"] = len(final_state.get("generated_chunks", []))
            final_state["stats"]["embeddings_generated"] = len(final_state.get("generated_embeddings", []))
            final_state["current_stage"] = "completed"
            
            logger.info("✅ LangGraph workflow completed successfully!")
            self._log_final_stats(final_state)
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ LangGraph workflow failed: {e}")
            raise

    async def search_documents(self, query: str, collection: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents using LangGraph workflow with semantic similarity"""
        try:
            logger.info(f"🔍 LangGraph search: '{query}' in {collection or 'all collections'}")
            
            # Initialize if not already done
            if not hasattr(self, 'compiled_graph'):
                await self.initialize()
            
            # Prepare search state
            search_state = {
                "query": query,
                "search_results": [],
                "reranked_results": [],
                "collection_name_pdf": self.collection_name_pdf,
                "collection_name_jira": self.collection_name_jira,
                "limit": limit,
                "stats": {
                    "start_time": datetime.now().isoformat(),
                    "search_query": query,
                    "target_collection": collection
                }
            }
            
            # Use search nodes from our workflow
            logger.info("🔍 LangGraph Node: Document Search")
            
            # Search in specified collection or both
            all_results = []
            
            if not collection or collection == "pdf_documents":
                try:
                    pdf_results = await self.pdf_qdrant_service.search_similar_async(
                        query=query,
                        collection_name=self.collection_name_pdf,
                        limit=limit
                    )
                    all_results.extend(pdf_results)
                    logger.info(f"Found {len(pdf_results)} PDF results")
                except Exception as e:
                    logger.warning(f"PDF search failed: {e}")
            
            if not collection or collection == "jira_tickets":
                try:
                    jira_results = await self.jira_qdrant_service.search_similar_async(
                        query=query,
                        collection_name=self.collection_name_jira,
                        limit=limit
                    )
                    all_results.extend(jira_results)
                    logger.info(f"Found {len(jira_results)} JIRA results")
                except Exception as e:
                    logger.warning(f"JIRA search failed: {e}")
            
            # Rerank results if we have multiple sources
            if len(all_results) > 1 and hasattr(self, 'reranker_service'):
                try:
                    reranked_results = await self.reranker_service.rerank_async(
                        query=query,
                        documents=[r.get("text", "") for r in all_results],
                        top_k=limit
                    )
                    
                    # Map reranked scores back to original results
                    final_results = []
                    for rank_result in reranked_results:
                        if rank_result.index < len(all_results):
                            result = all_results[rank_result.index].copy()
                            result["rerank_score"] = rank_result.score
                            final_results.append(result)
                    
                    all_results = final_results
                    logger.info(f"Reranked to {len(all_results)} results")
                    
                except Exception as e:
                    logger.warning(f"Reranking failed: {e}")
            
            # Sort by score (higher is better)
            all_results.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
            
            # Limit results
            final_results = all_results[:limit]
            
            logger.info(f"🔍 Search completed: {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _log_final_stats(self, state: DocumentProcessingState):
        """Log final processing statistics"""
        if state.get('stats'):
            stats = state['stats']
            logger.info(f"✅ Processing complete:")
            logger.info(f"   Documents processed: {stats.get('documents_processed', 0)}")
            logger.info(f"   Chunks created: {stats.get('chunks_created', 0)}")
            logger.info(f"   Embeddings generated: {stats.get('embeddings_generated', 0)}")
            logger.info(f"   Vectors stored: {stats.get('vectors_stored', 0)}")
    
    async def search_documents(self, 
                             query: str, 
                             collection: str = "both",
                             limit: int = 5,
                             use_reranking: bool = True) -> DocumentProcessingState:
        """
        Search documents using the LangGraph workflow
        
        Args:
            query: Search query
            collection: "pdf_documents", "jira_tickets", or "both"
            limit: Number of results to return
            use_reranking: Whether to apply cross-encoder reranking
            
        Returns:
            State with search results
        """
        if not self.compiled_graph:
            await self.initialize()
            
        logger.info(f"🔍 LangGraph search: '{query}' in {collection}")
        
        # Create search-specific workflow
        search_workflow = StateGraph(DocumentProcessingState)
        search_workflow.add_node("search", self._search_node)
        
        if use_reranking:
            search_workflow.add_node("rerank_results", self.nodes.rerank_results_node)
            search_workflow.add_edge(START, "search")
            search_workflow.add_edge("search", "rerank_results") 
            search_workflow.add_edge("rerank_results", END)
        else:
            search_workflow.add_edge(START, "search")
            search_workflow.add_edge("search", END)
        
        search_graph = search_workflow.compile()
        
        # Create search state
        search_state = self._create_initial_state(
            search_query=query,
            config={"rerank_top_k": limit}
        )
        search_state["services"] = {
            "embedding_service": self.nodes.embedding_service,
            "qdrant_service": self.nodes.qdrant_service,
            "reranker": self.nodes.reranker
        }
        
        # Execute search
        final_state = await search_graph.ainvoke(search_state)
        
        logger.info(f"🔍 Search completed: {len(final_state.get('reranked_results', final_state.get('search_results', [])))} results")
        return final_state
    
    async def _search_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Search node for finding similar documents"""
        logger.info("🔍 LangGraph Node: Document Search")
        
        query = state["search_query"]
        qdrant_service = state["services"]["qdrant_service"]
        embedding_service = state["services"]["embedding_service"]
        
        # Generate query embedding
        query_vector = embedding_service.get_embedding(query)
        
        search_results = []
        
        # Search PDF collection
        try:
            pdf_results = await qdrant_service.search_similar_async(
                collection_name=self.collection_name_pdf,
                query_vector=query_vector,
                limit=15  # Get more for reranking
            )
            
            for result in pdf_results:
                search_result = SearchResult(
                    chunk_id=result.get("id", ""),
                    similarity_score=result.get("score", 0.0),
                    chunk_text=result.get("payload", {}).get("text", ""),
                    metadata=result.get("payload", {})
                )
                search_results.append(search_result)
                
        except Exception as e:
            logger.warning(f"PDF search failed: {e}")
        
        # Search JIRA collection
        try:
            jira_results = await qdrant_service.search_similar_async(
                collection_name=self.collection_name_jira,
                query_vector=query_vector,
                limit=15  # Get more for reranking
            )
            
            for result in jira_results:
                search_result = SearchResult(
                    chunk_id=result.get("id", ""),
                    similarity_score=result.get("score", 0.0),
                    chunk_text=result.get("payload", {}).get("text", ""),
                    metadata=result.get("payload", {})
                )
                search_results.append(search_result)
                
        except Exception as e:
            logger.warning(f"JIRA search failed: {e}")
        
        state["search_results"] = search_results
        return state
    
    def _log_final_stats(self, state: DocumentProcessingState):
        """Log final processing statistics"""
        stats = state["stats"]
        
        logger.info("📊 LangGraph Processing Summary:")
        logger.info(f"   Documents processed: {stats['documents_processed']}")
        logger.info(f"   Chunks created: {stats['chunks_created']}")
        logger.info(f"   Embeddings generated: {stats['embeddings_generated']}")
        logger.info(f"   Vectors stored: {stats['vectors_stored']}")
        logger.info(f"   PDF vectors: {stats['pdf_vectors']}")
        logger.info(f"   JIRA vectors: {stats['jira_vectors']}")
        
        if state["errors"]:
            logger.warning(f"   Errors encountered: {len(state['errors'])}")
            for error in state["errors"]:
                logger.warning(f"     - {error}")


# Factory function
def create_dual_document_workflow(**kwargs) -> DualDocumentProcessingWorkflow:
    """
    Create a LangGraph dual document processing workflow
    
    Args:
        **kwargs: Configuration options
        
    Returns:
        Configured workflow instance
    """
    return DualDocumentProcessingWorkflow(**kwargs)