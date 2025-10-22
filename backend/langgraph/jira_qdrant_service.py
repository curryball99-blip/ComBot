"""
Enhanced Qdrant Service for JIRA Ticket Processing
=================================================

Extended Qdrant service optimized for storing and retrieving JIRA ticket chunks
with proper metadata handling and ticket-based collection organization.
"""

import asyncio
import numpy as np
import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import qdrant_client.models as models
from qdrant_client.http import models
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger(__name__)


class JiraQdrantService:
    """Enhanced Qdrant service for JIRA ticket processing"""
    
    def __init__(self, base_url: str = None):
        self.qdrant_url = base_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.client = None
        # Active embedding backend: BGE large (1024 dimensions)
        self.vector_size = 1024
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Collection naming strategy
        self.base_collection_name = "jira_tickets"
        self.global_collection_name = "jira_tickets_global"  # For cross-ticket search
        
        # Optimized search parameters
        self.default_limit = 10
        self.score_threshold = 0.6  # Higher threshold for better precision
        self.search_params = {
            "hnsw_ef": 64,
            "exact": False
        }
        
        # Initialize connection synchronously
        self._connect_sync()
        
    def _connect_sync(self):
        """Synchronous connection to Qdrant"""
        connection_attempts = [
            {"method": "configured_url", "client": lambda: QdrantClient(url=self.qdrant_url)},
            {"method": "localhost", "client": lambda: QdrantClient(host="localhost", port=6333)},
            {"method": "memory", "client": lambda: QdrantClient(location=":memory:")},
        ]
        
        for attempt in connection_attempts:
            try:
                method = attempt["method"]
                logger.info(f"Connecting to Qdrant via {method}...")
                
                self.client = attempt["client"]()
                
                # Test connection
                self.client.get_collections()
                
                logger.info(f"✅ Connected to Qdrant via {method}")
                return
                
            except Exception as e:
                logger.warning(f"Qdrant connection via {method} failed: {e}")
                continue
        
        logger.error("All Qdrant connection attempts failed")
        raise ConnectionError("Could not connect to Qdrant")
        
    async def initialize(self):
        """Initialize the Qdrant service"""
        await self._connect()
        await self._setup_global_collection()
        
    async def _connect(self):
        """Establish connection to Qdrant"""
        connection_attempts = [
            {"method": "configured_url", "client": lambda: QdrantClient(url=self.qdrant_url)},
            {"method": "localhost", "client": lambda: QdrantClient(host="localhost", port=6333)},
            {"method": "memory", "client": lambda: QdrantClient(location=":memory:")},
        ]
        
        for attempt in connection_attempts:
            try:
                method = attempt["method"]
                logger.info(f"Connecting to Qdrant via {method}...")
                
                self.client = attempt["client"]()
                
                # Test connection
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.client.get_collections
                )
                
                logger.info(f"✅ Connected to Qdrant via {method}")
                return
                
            except Exception as e:
                logger.warning(f"Qdrant connection via {method} failed: {e}")
                continue
        
        logger.error("All Qdrant connection attempts failed")
        raise ConnectionError("Could not connect to Qdrant")
    
    async def _setup_collection_by_name(self, collection_name: str, vector_size: int = None):
        """Setup a collection with a specific name"""
        # Use passed vector_size or fallback to self.vector_size
        effective_vector_size = vector_size if vector_size is not None else self.vector_size
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._setup_collection_by_name_sync, collection_name, effective_vector_size)

    def _setup_collection_by_name_sync(self, collection_name: str, vector_size: int):
        """Synchronous setup of collection by name"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == collection_name for col in collections)
            
            if not collection_exists:
                logger.info(f"Creating JIRA collection: {collection_name}")
                logger.info(f"🔍 Using vector dimension: {vector_size}")
                
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                        hnsw_config=models.HnswConfigDiff(
                            m=16,
                            ef_construct=100,
                            full_scan_threshold=5000,
                        )
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        default_segment_number=1,
                        max_segment_size=100000,
                        indexing_threshold=20000,
                    )
                )
                logger.info(f"✅ Collection '{collection_name}' created successfully with dimension {vector_size}")
            else:
                logger.info(f"Collection '{collection_name}' already exists")
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise

    async def _setup_global_collection(self, vector_size: int = None):
        """Setup the global collection for cross-ticket search"""
        # Use passed vector_size or fallback to self.vector_size
        effective_vector_size = vector_size if vector_size is not None else self.vector_size
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._setup_global_collection_sync, effective_vector_size)
    
    def _setup_global_collection_sync(self, vector_size: int):
        """Synchronous setup of global collection"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == self.global_collection_name for col in collections)
            
            if not collection_exists:
                logger.info(f"Creating global JIRA collection: {self.global_collection_name}")
                logger.info(f"🔍 Using vector dimension: {vector_size}")
                
                self.client.create_collection(
                    collection_name=self.global_collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                        hnsw_config=models.HnswConfigDiff(
                            m=16,
                            ef_construct=100,
                            full_scan_threshold=5000,
                        )
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        default_segment_number=1,
                        max_segment_size=100000,
                        memmap_threshold=50000,
                    )
                )
                logger.info("✅ Global JIRA collection created successfully")
            else:
                logger.info(f"Global collection {self.global_collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Failed to setup global collection: {e}")
            raise
    
    async def _setup_ticket_collection(self, ticket_key: str, vector_size: int = None):
        """Setup individual ticket collection"""
        collection_name = self._get_ticket_collection_name(ticket_key)
        # Use passed vector_size or fallback to self.vector_size
        effective_vector_size = vector_size if vector_size is not None else self.vector_size
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._setup_ticket_collection_sync,
            collection_name,
            effective_vector_size
        )
    
    def _setup_ticket_collection_sync(self, collection_name: str, vector_size: int):
        """Synchronous setup of ticket-specific collection"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == collection_name for col in collections)
            
            if not collection_exists:
                logger.info(f"Creating ticket collection: {collection_name}")
                logger.info(f"🔍 Using vector dimension: {vector_size}")
                
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                        hnsw_config=models.HnswConfigDiff(
                            m=8,  # Smaller M for individual tickets
                            ef_construct=50,
                            full_scan_threshold=1000,
                        )
                    )
                )
                logger.info(f"✅ Ticket collection {collection_name} created")
                
        except Exception as e:
            logger.error(f"Failed to setup ticket collection {collection_name}: {e}")
            raise
    
    def _get_ticket_collection_name(self, ticket_key: str) -> str:
        """Generate collection name for specific ticket"""
        # Clean ticket key for collection name
        clean_key = ticket_key.lower().replace('-', '_').replace(' ', '_')
        return f"{self.base_collection_name}_{clean_key}"
    
    async def ensure_collection_exists_async(self, collection_name: str, vector_size: int = None):
        """Ensure collection exists, creating it if necessary.

        If vector_size is None, use self.vector_size (default 1024 with BGE).
        Logs a warning if an existing collection has a mismatched dimension.
        """
        try:
            target_dimension = vector_size if vector_size is not None else self.vector_size
            if collection_name == self.global_collection_name:
                await self._setup_global_collection(target_dimension)
            elif collection_name == self.base_collection_name:
                # This is the main jira_tickets collection - create it directly
                await self._setup_collection_by_name(collection_name, target_dimension)
            else:
                # It's a ticket-specific collection - extract ticket key
                if collection_name.startswith(self.base_collection_name):
                    ticket_key = collection_name.replace(f"{self.base_collection_name}_", "")
                    await self._setup_ticket_collection(ticket_key, target_dimension)
                else:
                    # Fallback - setup as ticket collection with the full name
                    await self._setup_ticket_collection(collection_name, target_dimension)

            # Post-check: verify dimension matches expectation
            try:
                info = self.client.get_collection(collection_name)
                existing_dim = info.config.params.vectors.size
                if existing_dim != target_dimension:
                    logger.warning(f"⚠️ Dimension mismatch for '{collection_name}': stored={existing_dim} expected={target_dimension}. Consider re-ingesting or cleaning.")
            except Exception as dim_e:
                logger.debug(f"Dimension check skipped for {collection_name}: {dim_e}")
        except Exception as e:
            logger.error(f"Failed to ensure collection {collection_name} exists: {e}")
            raise
    
    async def upsert_embeddings(self, collection_name: str, points: List[Dict[str, Any]]):
        """Upsert embeddings to specified collection"""
        
        # Collection should already be created by ensure_collection_exists_async
        # No additional collection creation logic needed here
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._upsert_embeddings_sync,
            collection_name,
            points
        )
    
    def _upsert_embeddings_sync(self, collection_name: str, points: List[Dict[str, Any]]):
        """Synchronous upsert of embeddings"""
        try:
            # Convert points to PointStruct
            qdrant_points = []
            for point in points:
                qdrant_point = PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point["payload"]
                )
                qdrant_points.append(qdrant_point)
            
            # Upsert in smaller chunks to prevent timeouts
            chunk_size = 100  # Smaller chunks for large datasets
            total_points = len(qdrant_points)
            
            for i in range(0, total_points, chunk_size):
                chunk = qdrant_points[i:i+chunk_size]
                chunk_num = (i // chunk_size) + 1
                total_chunks = (total_points + chunk_size - 1) // chunk_size
                
                try:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=chunk,
                        wait=True  # Wait for completion to ensure consistency
                    )
                    logger.info(f"✅ Chunk {chunk_num}/{total_chunks}: Upserted {len(chunk)} points to {collection_name}")
                    
                except Exception as chunk_error:
                    logger.error(f"❌ Chunk {chunk_num}/{total_chunks} failed: {chunk_error}")
                    # Retry once with even smaller chunk
                    if len(chunk) > 10:
                        mini_chunk_size = 10
                        for j in range(0, len(chunk), mini_chunk_size):
                            mini_chunk = chunk[j:j+mini_chunk_size]
                            try:
                                self.client.upsert(
                                    collection_name=collection_name,
                                    points=mini_chunk,
                                    wait=True
                                )
                                logger.info(f"🔄 Retry successful: {len(mini_chunk)} points")
                            except Exception as mini_error:
                                logger.error(f"💥 Mini-chunk failed: {mini_error}")
                                raise
                    else:
                        raise chunk_error
            
            logger.info(f"Successfully upserted {total_points} points to {collection_name}")
            
        except Exception as e:
            logger.error(f"Error upserting to {collection_name}: {e}")
            raise
    
    async def add_documents_batch_async(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add batch of documents to Qdrant and return IDs"""
        try:
            if not documents:
                return []
                
            # Convert documents to points format expected by upsert_embeddings
            points = []
            ids = []
            
            for doc in documents:
                point_id = doc.get('id', str(uuid.uuid4()))
                ids.append(point_id)
                
                points.append({
                    'id': point_id,
                    'vector': doc['vector'],
                    'payload': doc.get('payload', {})
                })
            
            # Get collection name from payload
            collection_name = documents[0].get('payload', {}).get('collection_name', self.global_collection_name)
            
            # Ensure collection exists before upserting
            await self.ensure_collection_exists_async(collection_name)
            await self.upsert_embeddings(collection_name, points)
            
            logger.info(f"Successfully added {len(documents)} documents to {collection_name}")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding documents batch: {e}")
            logger.error(f"Sample document structure: {documents[0] if documents else 'No documents'}")

    async def search_similar_async(self, query: str, collection_name: str, limit: int = 10, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents using semantic similarity"""
        try:
            # Generate embedding for the query
            from embedding_bge_service import create_bge_embedding_service
            embedding_service = create_bge_embedding_service()
            
            # Get query embedding
            query_embedding = await embedding_service.get_embeddings_batch_async([query])
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search in Qdrant
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self._search_similar_sync,
                collection_name,
                query_embedding[0],  # query_embedding is a list of floats already
                limit,
                score_threshold
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    def _search_similar_sync(self, collection_name: str, query_vector: List[float], limit: int, score_threshold: float) -> List[Dict[str, Any]]:
        """Synchronous semantic search"""
        try:
            from qdrant_client.models import SearchRequest
            
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "text": result.payload.get("text", ""),
                    "metadata": {
                        "ticket_key": result.payload.get("ticket_key", ""),
                        "summary": result.payload.get("summary", ""),
                        "status": result.payload.get("status", ""),
                        "assignee": result.payload.get("assignee", ""),
                        "priority": result.payload.get("priority", ""),
                        "chunk_type": result.payload.get("chunk_type", ""),
                        "collection_name": result.payload.get("collection_name", "")
                    }
                })
            
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Error in synchronous search: {e}")
            return []

    async def list_collections(self) -> List[Dict[str, Any]]:
            raise
    
    async def search_ticket(self, 
                           ticket_key: str, 
                           query_vector: List[float], 
                           limit: int = 5,
                           score_threshold: float = None) -> List[Dict[str, Any]]:
        """Search within a specific ticket"""
        
        collection_name = self._get_ticket_collection_name(ticket_key)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._search_sync,
            collection_name,
            query_vector,
            limit,
            score_threshold or self.score_threshold,
            {"ticket_key": ticket_key}
        )
    
    async def search_all_tickets(self,
                                query_vector: List[float],
                                limit: int = 10,
                                score_threshold: float = None,
                                filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search across all tickets"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._search_sync,
            self.global_collection_name,
            query_vector,
            limit,
            score_threshold or self.score_threshold,
            filters
        )
    
    def _search_sync(self,
                    collection_name: str,
                    query_vector: List[float],
                    limit: int,
                    score_threshold: float,
                    filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Synchronous search implementation"""
        try:
            # Build filter if provided
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                search_params=models.SearchParams(
                    hnsw_ef=self.search_params["hnsw_ef"],
                    exact=self.search_params["exact"]
                )
            )
            
            # Format results
            results = []
            for hit in search_results:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} results in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search error in {collection_name}: {e}")
            return []
    
    async def get_ticket_stats(self, ticket_key: str) -> Dict[str, Any]:
        """Get statistics for a specific ticket"""
        
        collection_name = self._get_ticket_collection_name(ticket_key)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._get_collection_stats_sync,
            collection_name
        )
    
    def _get_collection_stats_sync(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            collection_info = self.client.get_collection(collection_name)
            
            return {
                "collection_name": collection_name,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for {collection_name}: {e}")
            return {}
    
    async def list_ticket_collections(self) -> List[str]:
        """List all ticket-specific collections"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._list_ticket_collections_sync
        )
    
    def _list_ticket_collections_sync(self) -> List[str]:
        """Synchronous listing of ticket collections"""
        try:
            collections = self.client.get_collections().collections
            ticket_collections = [
                col.name for col in collections 
                if col.name.startswith(self.base_collection_name) and 
                col.name != self.global_collection_name
            ]
            
            return ticket_collections
            
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    async def delete_ticket_collection(self, ticket_key: str):
        """Delete a specific ticket collection"""
        
        collection_name = self._get_ticket_collection_name(ticket_key)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._delete_collection_sync,
            collection_name
        )
    
    def _delete_collection_sync(self, collection_name: str):
        """Synchronous collection deletion"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {e}")
            raise
    
    def create_collection(self, collection_name: str, vector_dimension: int):
        """Create a collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == collection_name for col in collections)
            
            if not collection_exists:
                logger.info(f"Creating collection: {collection_name}")
                
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_dimension,
                        distance=Distance.COSINE,
                        hnsw_config=models.HnswConfigDiff(
                            m=16,
                            ef_construct=100,
                            full_scan_threshold=5000,
                        )
                    )
                )
                logger.info(f"✅ Collection {collection_name} created successfully")
            else:
                logger.info(f"Collection {collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise
    
    def store_vectors(self, collection_name: str, points: List[Dict[str, Any]]):
        """Store vectors in the specified collection"""
        try:
            # Convert points to PointStruct
            qdrant_points = []
            for point in points:
                qdrant_point = PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point["payload"]
                )
                qdrant_points.append(qdrant_point)
            
            # Upsert points
            self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points
            )
            
            logger.info(f"Successfully stored {len(qdrant_points)} vectors in {collection_name}")
            
        except Exception as e:
            logger.error(f"Error storing vectors in {collection_name}: {e}")
            raise
    
    def search_similar(self, collection_name: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors in the collection"""
        try:
            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=self.score_threshold,
                search_params=models.SearchParams(
                    hnsw_ef=self.search_params["hnsw_ef"],
                    exact=self.search_params["exact"]
                )
            )
            
            # Format results
            results = []
            for hit in search_results:
                result = {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar vectors in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search error in {collection_name}: {e}")
            return []
    
    def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            collections = self.client.get_collections().collections
            return [col.name for col in collections]
        except Exception as e:
            logger.warning(f"Error listing collections: {e}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection"""
        try:
            collection_info = self.client.get_collection(collection_name)
            
            return {
                "collection_name": collection_name,
                "vectors_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance
            }
            
        except Exception as e:
            logger.error(f"Error getting info for {collection_name}: {e}")
            return {}
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {e}")
            raise
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Maintain backward compatibility
QdrantService = JiraQdrantService