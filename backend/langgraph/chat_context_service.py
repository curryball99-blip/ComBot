"""
Chat Context Service
===================

Service for managing chat sessions and message history using Qdrant as the storage backend.
Stores chat sessions and messages with proper indexing for efficient retrieval.

Features:
- Create and manage chat sessions with unique IDs
- Store conversation history with message pairs (user + assistant)
- Retrieve chat history for context in LLM conversations
- Delete individual messages or entire chat sessions
- Efficient querying with session-based filtering
"""

import asyncio
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import httpx
import os

# Try to import available embedding service
try:
    from embedding_service_factory import create_embedding_backend
    EmbeddingService = create_embedding_backend
except ImportError:
    try:
        from embedding_bge_service import BGEEmbeddingService as EmbeddingService
    except ImportError:
        EmbeddingService = None

logger = logging.getLogger(__name__)

class ChatContextService:
    def __init__(self, qdrant_url: str = None, embedding_service = None):
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.embedding_service = embedding_service
        self.sessions_collection = "chat_sessions"
        self.messages_collection = "chat_messages"
        self.max_history_length = 50  # Maximum messages per session to keep in context
        self.max_context_tokens = 4000  # Approximate token limit for context
        
    async def initialize(self):
        """Initialize Qdrant collections for chat storage"""
        try:
            # Create chat sessions collection
            await self._create_collection_if_not_exists(
                collection_name=self.sessions_collection,
                vector_size=384,  # For session embeddings if needed
                description="Chat sessions metadata"
            )
            
            # Create chat messages collection
            await self._create_collection_if_not_exists(
                collection_name=self.messages_collection,
                vector_size=384,  # For message embeddings if needed
                description="Chat messages and conversation history"
            )
            
            logger.info("✅ Chat context service initialized with Qdrant collections")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize chat context service: {e}")
            return False
    
    async def _create_collection_if_not_exists(self, collection_name: str, vector_size: int, description: str):
        """Create Qdrant collection if it doesn't exist"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if collection exists
            try:
                resp = await client.get(f"{self.qdrant_url}/collections/{collection_name}")
                if resp.status_code == 200:
                    logger.info(f"Collection {collection_name} already exists")
                    return
            except:
                pass
            
            # Create collection
            collection_config = {
                "vectors": {
                    "size": vector_size,
                    "distance": "Cosine"
                }
            }
            
            resp = await client.put(
                f"{self.qdrant_url}/collections/{collection_name}",
                json=collection_config
            )
            
            if resp.status_code in [200, 201]:
                logger.info(f"✅ Created collection: {collection_name}")
            else:
                raise Exception(f"Failed to create collection {collection_name}: {resp.status_code} {resp.text}")
    
    async def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "title": title or "New Conversation",
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0,
            "last_message_preview": "",
            "status": "active"
        }
        
        try:
            # Generate a simple embedding for the session (title + metadata)
            embedding_text = f"{session_data['title']} {session_data['user_id']}"
            vector = [0.0] * 384  # Default vector
            
            if self.embedding_service:
                try:
                    vector = self.embedding_service.get_embeddings([embedding_text])[0]
                except:
                    logger.warning("Failed to generate session embedding, using default")
            
            # Store session in Qdrant
            point_data = {
                "id": session_id,
                "vector": vector,
                "payload": session_data
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.put(
                    f"{self.qdrant_url}/collections/{self.sessions_collection}/points",
                    json={"points": [point_data]}
                )
                
                if resp.status_code not in [200, 201]:
                    raise Exception(f"Failed to store session: {resp.status_code} {resp.text}")
            
            logger.info(f"✅ Created chat session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create chat session: {e}")
            raise
    
    async def add_message(self, session_id: str, user_message: str, assistant_response: str, 
                         sources: List[Dict[str, Any]] = None) -> str:
        """Add a message pair to the conversation"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message_data = {
            "message_id": message_id,
            "session_id": session_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "sources": sources or [],
            "timestamp": timestamp,
            "message_type": "conversation_pair"
        }
        
        try:
            # Generate embedding for the message pair (for future semantic search)
            embedding_text = f"User: {user_message}\nAssistant: {assistant_response}"
            vector = [0.0] * 384  # Default vector
            
            if self.embedding_service:
                try:
                    vector = self.embedding_service.get_embeddings([embedding_text])[0]
                except:
                    logger.warning("Failed to generate message embedding, using default")
            
            # Store message in Qdrant
            point_data = {
                "id": message_id,
                "vector": vector,
                "payload": message_data
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Store the message
                resp = await client.put(
                    f"{self.qdrant_url}/collections/{self.messages_collection}/points",
                    json={"points": [point_data]}
                )
                
                if resp.status_code not in [200, 201]:
                    raise Exception(f"Failed to store message: {resp.status_code} {resp.text}")
            
            # Update session metadata
            await self._update_session_metadata(session_id, user_message[:100])
            
            logger.info(f"✅ Added message to session {session_id}: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add message to session {session_id}: {e}")
            raise
    
    async def _update_session_metadata(self, session_id: str, last_message_preview: str):
        """Update session metadata after adding a message"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get current session data
                resp = await client.post(
                    f"{self.qdrant_url}/collections/{self.sessions_collection}/points/scroll",
                    json={
                        "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]},
                        "limit": 1,
                        "with_payload": True
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    points = data.get('result', {}).get('points', [])
                    
                    if points:
                        session_data = points[0]['payload']
                        session_data['updated_at'] = datetime.now().isoformat()
                        session_data['message_count'] = session_data.get('message_count', 0) + 1
                        session_data['last_message_preview'] = last_message_preview
                        
                        # Update the session point
                        update_data = {
                            "points": [{
                                "id": session_id,
                                "vector": points[0]['vector'],
                                "payload": session_data
                            }]
                        }
                        
                        await client.put(
                            f"{self.qdrant_url}/collections/{self.sessions_collection}/points",
                            json=update_data
                        )
                        
        except Exception as e:
            logger.warning(f"Failed to update session metadata: {e}")
    
    async def get_chat_history(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Retrieve chat history for a session"""
        try:
            limit = limit or self.max_history_length
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.qdrant_url}/collections/{self.messages_collection}/points/scroll",
                    json={
                        "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]},
                        "limit": limit,
                        "with_payload": True
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    points = data.get('result', {}).get('points', [])
                    
                    # Sort by timestamp (oldest first for conversation flow)
                    messages = []
                    for point in points:
                        payload = point['payload']
                        messages.append({
                            "message_id": payload['message_id'],
                            "user_message": payload['user_message'],
                            "assistant_response": payload['assistant_response'],
                            "sources": payload.get('sources', []),
                            "timestamp": payload['timestamp']
                        })
                    
                    # Sort by timestamp
                    messages.sort(key=lambda x: x['timestamp'])
                    
                    # Limit to recent messages if too many
                    if len(messages) > limit:
                        messages = messages[-limit:]
                    
                    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
                    return messages
                    
                else:
                    logger.warning(f"Failed to retrieve chat history: {resp.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get chat history for session {session_id}: {e}")
            return []
    
    async def list_sessions(self, user_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List chat sessions for a user"""
        try:
            filter_conditions = []
            if user_id:
                filter_conditions.append({"key": "user_id", "match": {"value": user_id}})
            
            query_filter = {"must": filter_conditions} if filter_conditions else None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                body = {
                    "limit": limit,
                    "with_payload": True
                }
                if query_filter:
                    body["filter"] = query_filter
                
                resp = await client.post(
                    f"{self.qdrant_url}/collections/{self.sessions_collection}/points/scroll",
                    json=body
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    points = data.get('result', {}).get('points', [])
                    
                    sessions = []
                    for point in points:
                        payload = point['payload']
                        sessions.append({
                            "session_id": payload['session_id'],
                            "title": payload['title'],
                            "user_id": payload['user_id'],
                            "created_at": payload['created_at'],
                            "updated_at": payload['updated_at'],
                            "message_count": payload.get('message_count', 0),
                            "last_message_preview": payload.get('last_message_preview', ''),
                            "status": payload.get('status', 'active')
                        })
                    
                    # Sort by updated time (most recent first)
                    sessions.sort(key=lambda x: x['updated_at'], reverse=True)
                    
                    logger.info(f"Listed {len(sessions)} sessions")
                    return sessions
                    
                else:
                    logger.warning(f"Failed to list sessions: {resp.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Delete all messages in the session
                await client.post(
                    f"{self.qdrant_url}/collections/{self.messages_collection}/points/delete",
                    json={
                        "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]}
                    }
                )
                
                # Delete the session itself
                await client.post(
                    f"{self.qdrant_url}/collections/{self.sessions_collection}/points/delete",
                    json={
                        "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]}
                    }
                )
                
                logger.info(f"✅ Deleted session {session_id} and all its messages")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to delete session {session_id}: {e}")
            return False
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a specific message"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.qdrant_url}/collections/{self.messages_collection}/points/delete",
                    json={
                        "filter": {"must": [{"key": "message_id", "match": {"value": message_id}}]}
                    }
                )
                
                if resp.status_code == 200:
                    logger.info(f"✅ Deleted message {message_id}")
                    return True
                else:
                    logger.warning(f"Failed to delete message {message_id}: {resp.status_code}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Failed to delete message {message_id}: {e}")
            return False
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.qdrant_url}/collections/{self.sessions_collection}/points/scroll",
                    json={
                        "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]},
                        "limit": 1,
                        "with_payload": True
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    points = data.get('result', {}).get('points', [])
                    
                    if points:
                        return points[0]['payload']
                    
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    def format_chat_history_for_context(self, messages: List[Dict[str, Any]], max_tokens: int = None) -> str:
        """Format chat history for inclusion in LLM context"""
        if not messages:
            return ""
        
        max_tokens = max_tokens or self.max_context_tokens
        
        # Format messages as conversation with better structure
        formatted_parts = []
        for i, msg in enumerate(messages, 1):
            user_msg = msg['user_message'].strip()
            assistant_msg = msg['assistant_response'].strip()
            
            # Add message numbering and cleaner formatting
            formatted_parts.append(f"Message {i}:")
            formatted_parts.append(f"User: {user_msg}")
            formatted_parts.append(f"Assistant: {assistant_msg}")
            
            # Add sources info if available
            sources = msg.get('sources', [])
            if sources:
                ticket_keys = [s.get('ticket_key') for s in sources if s.get('ticket_key')]
                if ticket_keys:
                    unique_tickets = list(set(ticket_keys))[:3]  # Show max 3 tickets
                    formatted_parts.append(f"Referenced: {', '.join(unique_tickets)}")
        
        full_context = "\n".join(formatted_parts)
        
        # Truncate if too long (approximate token count: 1 token ≈ 4 characters)
        if len(full_context) > max_tokens * 4:
            # Keep the most recent complete message exchanges that fit within token limit
            truncated_parts = []
            char_count = 0
            
            # Work backwards through messages (4 lines per message: Message X, User, Assistant, [Referenced])
            i = len(formatted_parts) - 1
            while i >= 0:
                # Find the start of this message block
                msg_start = i
                while msg_start >= 0 and not formatted_parts[msg_start].startswith("Message "):
                    msg_start -= 1
                
                if msg_start < 0:
                    break
                
                # Calculate size of this message block
                msg_block = formatted_parts[msg_start:i+1]
                block_size = sum(len(part) for part in msg_block) + len(msg_block)  # +newlines
                
                if char_count + block_size <= max_tokens * 4:
                    truncated_parts = msg_block + truncated_parts
                    char_count += block_size
                    i = msg_start - 1
                else:
                    break
            
            full_context = "\n".join(truncated_parts)
            if len(truncated_parts) < len(formatted_parts):
                full_context = "[...earlier conversation truncated...]\n" + full_context
        
        if full_context:
            return f"[CONVERSATION HISTORY - {len(messages)} previous exchanges]\n{full_context}\n[END HISTORY]\n\n"
        
        return ""