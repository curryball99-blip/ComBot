"""
JIRA Ticket Processor for Documents Directory
============================================

Processes JIRA tickets from /home/ubuntu/Ravi/ComBot/backend/documents/
- Rich metadata extraction and preservation
 - Uses BGE embeddings (1024-d)
- Stores in shared Qdrant database with collection: jira_tickets
"""

import os
import logging
import json
import hashlib
import re
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import re

logger = logging.getLogger(__name__)

@dataclass
class JIRATicket:
    """Represents a JIRA ticket with rich metadata"""
    key: str
    summary: str
    description: str
    status: str
    assignee: str
    reporter: str
    created: str
    updated: str
    priority: str
    issue_type: str
    project: str
    components: List[str]
    labels: List[str]
    comments: List[str]
    raw_data: Dict[str, Any]

@dataclass
class JIRAChunk:
    """Represents a chunk of text from a JIRA ticket"""
    chunk_id: str
    text: str
    ticket_id: str
    chunk_index: int
    chunk_type: str  # 'summary', 'description', 'comment', 'combined'
    metadata: Dict[str, Any]

class JIRATicketProcessor:
    """
    JIRA ticket processor with rich metadata handling for documents directory
    """
    
    def __init__(self, 
                 embedding_service,
                 qdrant_service,
                 documents_path: str = "/home/ubuntu/Ravi/ComBot/backend/documents/",
                 chunk_size: int = 800,
                 chunk_overlap: int = 150):
        """
        Initialize JIRA ticket processor
        
        Args:
            embedding_service: BGE embedding service instance
            qdrant_service: Qdrant service for vector storage
            documents_path: Path to JIRA ticket files
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service
        self.documents_path = Path(documents_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection_name = "jira_tickets"
        
        # Ensure documents directory exists
        self.documents_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized JIRA processor for: {self.documents_path}")
        logger.info(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    
    def parse_ticket_file(self, file_path: str) -> List[JIRATicket]:
        """
        Parse JIRA tickets from various file formats
        
        Args:
            file_path: Path to ticket file
            
        Returns:
            List of JIRATicket objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.json':
                return self._parse_json_tickets(content, file_path)
            elif file_ext == '.txt':
                return self._parse_text_tickets(content, file_path)
            else:
                # Try to detect format
                try:
                    json.loads(content)
                    return self._parse_json_tickets(content, file_path)
                except:
                    return self._parse_text_tickets(content, file_path)
                    
        except Exception as e:
            logger.error(f"Error parsing ticket file {file_path}: {e}")
            return []
    
    def _parse_json_tickets(self, content: str, file_path: str) -> List[JIRATicket]:
        """Parse JSON format tickets"""
        try:
            data = json.loads(content)
            tickets = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                ticket_list = data
            elif isinstance(data, dict):
                if 'issues' in data:
                    ticket_list = data['issues']
                elif 'tickets' in data:
                    ticket_list = data['tickets']
                else:
                    ticket_list = [data]  # Single ticket
            else:
                logger.warning(f"Unexpected JSON structure in {file_path}")
                return []
            
            for ticket_data in ticket_list:
                ticket = self._create_ticket_from_dict(ticket_data, file_path)
                if ticket:
                    tickets.append(ticket)
            
            logger.info(f"Parsed {len(tickets)} tickets from JSON file: {Path(file_path).name}")
            return tickets
            
        except Exception as e:
            logger.error(f"Error parsing JSON tickets from {file_path}: {e}")
            return []
    
    def _parse_text_tickets(self, content: str, file_path: str) -> List[JIRATicket]:
        """Parse text format tickets (pipe-separated or other formats)"""
        try:
            tickets = []
            lines = content.strip().split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Try pipe-separated format: KEY|SUMMARY|DESCRIPTION|STATUS|ASSIGNEE|CREATED
                if '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 3:  # At least key, summary, description
                        ticket_data = {
                            'key': parts[0] if len(parts) > 0 else f"UNKNOWN-{line_num}",
                            'summary': parts[1] if len(parts) > 1 else "No summary",
                            'description': parts[2] if len(parts) > 2 else "No description",
                            'status': parts[3] if len(parts) > 3 else "Unknown",
                            'assignee': parts[4] if len(parts) > 4 else "Unassigned",
                            'created': parts[5] if len(parts) > 5 else datetime.now().isoformat(),
                            'file_path': file_path,
                            'line_number': line_num
                        }
                        
                        ticket = self._create_ticket_from_dict(ticket_data, file_path)
                        if ticket:
                            tickets.append(ticket)
                else:
                    # Try to extract ticket key from line
                    ticket_key_match = re.search(r'([A-Z]+-\d+)', line)
                    if ticket_key_match:
                        ticket_key = ticket_key_match.group(1)
                        ticket_data = {
                            'key': ticket_key,
                            'summary': line[:100] + "..." if len(line) > 100 else line,
                            'description': line,
                            'status': "Unknown",
                            'assignee': "Unassigned",
                            'created': datetime.now().isoformat(),
                            'file_path': file_path,
                            'line_number': line_num
                        }
                        
                        ticket = self._create_ticket_from_dict(ticket_data, file_path)
                        if ticket:
                            tickets.append(ticket)
            
            logger.info(f"Parsed {len(tickets)} tickets from text file: {Path(file_path).name}")
            return tickets
            
        except Exception as e:
            logger.error(f"Error parsing text tickets from {file_path}: {e}")
            return []
    
    def _create_ticket_from_dict(self, data: Dict[str, Any], file_path: str) -> Optional[JIRATicket]:
        """Create JIRATicket from dictionary data"""
        try:
            # Extract fields with fallbacks
            key = data.get('key', data.get('id', f"UNKNOWN-{hash(str(data))}"[:10]))
            summary = data.get('summary', data.get('title', "No summary"))
            description = data.get('description', data.get('body', data.get('content', "")))
            # Custom fields (flatten later) - handle presence early so we can enrich description if needed
            custom_fields = data.get('custom_fields', {}) or {}
            l1_l2_analysis = custom_fields.get('l1_l2_analysis') or custom_fields.get('l1_analysis') or ''
            l3_engineer_analysis = custom_fields.get('l3_engineer_analysis') or custom_fields.get('l3_analysis') or ''
            rca_url = custom_fields.get('rca_url', '')
            fixed_version = custom_fields.get('fixed_version', '')
            crucible_review_id = custom_fields.get('crucible_review_id', '')
            rfr_rcc_id = custom_fields.get('rfr___rcc_id', custom_fields.get('rfr_rcc_id', ''))
            
            # Handle nested structures (like JIRA API responses)
            if 'fields' in data:
                fields = data['fields']
                summary = fields.get('summary', summary)
                description = fields.get('description', description)
                status = fields.get('status', {}).get('name', 'Unknown') if isinstance(fields.get('status'), dict) else str(fields.get('status', 'Unknown'))
                assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(fields.get('assignee'), dict) else str(fields.get('assignee', 'Unassigned'))
                reporter = fields.get('reporter', {}).get('displayName', 'Unknown') if isinstance(fields.get('reporter'), dict) else str(fields.get('reporter', 'Unknown'))
                priority = fields.get('priority', {}).get('name', 'Unknown') if isinstance(fields.get('priority'), dict) else str(fields.get('priority', 'Unknown'))
                issue_type = fields.get('issuetype', {}).get('name', 'Unknown') if isinstance(fields.get('issuetype'), dict) else str(fields.get('issuetype', 'Unknown'))
                created = fields.get('created') or fields.get('created_at') or data.get('created_at') or datetime.now().isoformat()
                updated = fields.get('updated') or fields.get('updated_at') or data.get('updated_at') or datetime.now().isoformat()
                project = fields.get('project', {}).get('key', 'UNKNOWN') if isinstance(fields.get('project'), dict) else str(fields.get('project', 'UNKNOWN'))
                components = [c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in fields.get('components', [])]
                labels = fields.get('labels', [])
                
                # Extract comments
                comments = []
                if 'comment' in fields and 'comments' in fields['comment']:
                    for comment in fields['comment']['comments']:
                        comment_text = comment.get('body', '')
                        if comment_text:
                            comments.append(comment_text)
            else:
                status = str(data.get('status', 'Unknown'))
                assignee = str(data.get('assignee', 'Unassigned'))
                reporter = str(data.get('reporter', 'Unknown'))
                priority = str(data.get('priority', 'Unknown'))
                issue_type = str(data.get('issue_type', data.get('type', 'Unknown')))
                created = data.get('created') or data.get('created_at') or datetime.now().isoformat()
                updated = data.get('updated') or data.get('updated_at') or datetime.now().isoformat()
                project = str(data.get('project', 'UNKNOWN'))
                components = data.get('components', [])
                labels = data.get('labels', [])
                
                # Extract comment text from comment objects
                comments = []
                comment_data = data.get('comments', [])
                for comment in comment_data:
                    if isinstance(comment, dict):
                        comment_text = comment.get('body', '')
                        if comment_text:
                            comments.append(comment_text)
                    else:
                        # If it's already a string, use it directly
                        if str(comment).strip():
                            comments.append(str(comment))
            
            # Clean text fields
            if isinstance(description, dict):
                description = str(description)
            
            # Attach custom field enrichments into raw data for transparency
            data['__enrichment'] = {
                'l1_l2_analysis': l1_l2_analysis,
                'l3_engineer_analysis': l3_engineer_analysis,
                'rca_url': rca_url,
                'fixed_version': fixed_version,
                'crucible_review_id': crucible_review_id,
                'rfr_rcc_id': rfr_rcc_id,
            }

            # Dynamically extend the JIRATicket dataclass attributes by storing enrichments in raw_data only.
            ticket = JIRATicket(
                key=key,
                summary=summary,
                description=description,
                status=status,
                assignee=assignee,
                reporter=reporter,
                created=created,
                updated=updated,
                priority=priority,
                issue_type=issue_type,
                project=project,
                components=components if isinstance(components, list) else [str(components)],
                labels=labels if isinstance(labels, list) else [str(labels)],
                comments=comments if isinstance(comments, list) else [str(comments)],
                raw_data=data
            )
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error creating ticket from data: {e}")
            logger.debug(f"Problematic data: {data}")
            return None
    
    def create_ticket_chunks(self, ticket: JIRATicket) -> List[JIRAChunk]:
        """
        Create chunks from a JIRA ticket with rich metadata
        
        Args:
            ticket: JIRATicket instance
            
        Returns:
            List of JIRAChunk objects
        """
        chunks = []
        
        # Combine all text fields for comprehensive embedding (ENRICHED)
        enrichment = ticket.raw_data.get('__enrichment', {})
        l1_l2_analysis = enrichment.get('l1_l2_analysis', '') or ''
        l3_engineer_analysis = enrichment.get('l3_engineer_analysis', '') or ''
        rca_url = enrichment.get('rca_url', '') or ''
        fixed_version = enrichment.get('fixed_version', '') or ''
        rfr_rcc_id = enrichment.get('rfr_rcc_id', '') or ''

        combined_text_parts = []
        if ticket.summary and ticket.summary.strip():
            combined_text_parts.append(f"Summary:\n{ticket.summary.strip()}")
        if ticket.description and ticket.description.strip():
            combined_text_parts.append(f"Description:\n{ticket.description.strip()}")
        if l1_l2_analysis.strip():
            combined_text_parts.append(f"L1/L2 Analysis:\n{l1_l2_analysis.strip()}")
        if l3_engineer_analysis.strip():
            combined_text_parts.append(f"L3 Engineer Analysis:\n{l3_engineer_analysis.strip()}")
        if fixed_version.strip():
            combined_text_parts.append(f"Fixed / Target Version:\n{fixed_version.strip()}")
        if rfr_rcc_id.strip():
            combined_text_parts.append(f"RFR/RCC ID:\n{rfr_rcc_id.strip()}")
        if rca_url.strip():
            combined_text_parts.append(f"RCA URL:\n{rca_url.strip()}")

        # Concatenate comments (retain numbering). Limit extremely long single comments to avoid blow-up.
        for i, comment in enumerate(ticket.comments):
            if not comment or not str(comment).strip():
                continue
            trimmed_comment = str(comment).strip()
            if len(trimmed_comment) > 5000:  # safety cap per comment
                trimmed_comment = trimmed_comment[:5000] + '... [TRUNCATED]'
            combined_text_parts.append(f"Comment {i+1}:\n{trimmed_comment}")

        combined_text = "\n\n".join(combined_text_parts)
        
        if not combined_text.strip():
            logger.warning(f"No text content for ticket {ticket.key}")
            return []
        
        # Create base metadata
        # Determine resolved flag
        status_norm = (ticket.status or '').strip().lower()
        is_resolved = status_norm in {'done','closed','resolved'}

        # --- Embedding model version (for lineage) ---
        embedding_version = getattr(self.embedding_service, 'model_name', 'unknown_model')

        # --- Keyword / keyphrase extraction (simple heuristic) ---
        def extract_keywords(text: str, max_terms: int = 25) -> List[str]:
            import re, math
            if not text:
                return []
            # Basic cleanup
            lowered = text.lower()
            tokens = re.findall(r"[a-z0-9_\-]{3,}", lowered)
            if not tokens:
                return []
            stop = {
                'the','and','with','from','this','that','have','for','are','you','your','was','were','been','will','would','shall','could','should','their','there','about','into','over','under','none','null','true','false','upon','each','only','other','more','some','than','can','cannot','while','after','before','when','what','which','where','why','how','also','but','not','our','its','any','all','per','via'
            }
            freq = {}
            for t in tokens:
                if t in stop or t.isdigit():
                    continue
                # Filter out very generic jira-ish words
                if t in {'ticket','issue','error','failed','failure','fix','fixes','added','adding','updated','update','component','version','build','test','tests','testing','code','stack','trace','log','logs'}:
                    continue
                freq[t] = freq.get(t, 0) + 1
            if not freq:
                return []
            # Score = raw freq * log(len(tokens)/freq)
            total_tokens = len(tokens)
            scored = [
                ( (c * math.log((total_tokens+1)/(c+1))), term ) for term, c in freq.items()
            ]
            scored.sort(reverse=True)
            return [term for _, term in scored[:max_terms]]

        keyword_source_text = "\n".join([
            ticket.summary or '',
            ticket.description or '',
            l1_l2_analysis or '',
            l3_engineer_analysis or '',
            "\n".join(ticket.comments[:10])  # limit early comments for keyword extraction
        ])[:25000]
        keywords = extract_keywords(keyword_source_text)

        base_metadata = {
            "ticket_key": ticket.key,
            "summary": ticket.summary,
            "status": ticket.status,
            "assignee": ticket.assignee,
            "reporter": ticket.reporter,
            "created": ticket.created,
            "updated": ticket.updated,
            "priority": ticket.priority,
            "issue_type": ticket.issue_type,
            "project": ticket.project,
            "components": ticket.components,
            "labels": ticket.labels,
            "content_type": "jira_ticket",
            "processed_at": datetime.now().isoformat(),
            "char_count": len(combined_text),
            "word_count": len(combined_text.split()),
            "comment_count": len(ticket.comments),
            # Enrichment specific metadata for downstream filtering / prompt construction
            "ingestion_version": "v3_resolved_flag_2025-09-30",
            "has_l1_l2_analysis": bool(l1_l2_analysis.strip()),
            "has_l3_engineer_analysis": bool(l3_engineer_analysis.strip()),
            "has_rca_url": bool(rca_url.strip()),
            "l1_l2_analysis": l1_l2_analysis.strip()[:8000] if l1_l2_analysis else "",
            "l3_engineer_analysis": l3_engineer_analysis.strip()[:8000] if l3_engineer_analysis else "",
            "rca_url": rca_url.strip(),
            "fixed_version": fixed_version.strip(),
            "rfr_rcc_id": rfr_rcc_id.strip(),
            "description_full": (ticket.description or "")[:12000],
            "comments_concat": "\n---\n".join([c[:4000] for c in ticket.comments])[:20000],
            "is_resolved": is_resolved,
            # New lineage & lexical assist fields
            "embedding_version": embedding_version,
            "keywords": keywords
        }
        
        # Generate UUID-based chunk ID for Qdrant compatibility
        import hashlib
        safe_ticket_key = re.sub(r'[^a-zA-Z0-9_-]', '_', ticket.key)[:50]  # Clean and limit length
        chunk_id = str(uuid.uuid4())
        
        # If combined text is short enough, create single chunk
        if len(combined_text) <= self.chunk_size:
            chunk = JIRAChunk(
                chunk_id=chunk_id,
                text=combined_text,
                ticket_id=ticket.key,
                chunk_index=0,
                chunk_type="combined",
                metadata={
                    **base_metadata,
                    "chunk_id": chunk_id,
                    "chunk_type": "combined",
                    "original_chunk_id": f"{safe_ticket_key}_combined_0"
                }
            )
            chunks.append(chunk)
        else:
            # Split into smaller chunks
            words = combined_text.split()
            chunk_index = 0
            start = 0
            
            while start < len(words):
                # Calculate chunk size in words (rough estimate)
                words_per_chunk = self.chunk_size // 5  # Rough estimate
                end = min(start + words_per_chunk, len(words))
                
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                
                if chunk_text.strip():
                    safe_chunk_id = str(uuid.uuid4())
                    chunk = JIRAChunk(
                        chunk_id=safe_chunk_id,
                        text=chunk_text,
                        ticket_id=ticket.key,
                        chunk_index=chunk_index,
                        chunk_type="partial",
                        metadata={
                            **base_metadata,
                            "chunk_id": safe_chunk_id,
                            "chunk_type": "partial",
                            "original_chunk_id": f"{safe_ticket_key}_partial_{chunk_index}",
                            "chunk_start_word": start,
                            "chunk_end_word": end
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Move with overlap
                overlap_words = self.chunk_overlap // 5
                start = max(end - overlap_words, start + 1)
                
                if end >= len(words):
                    break
        
        logger.debug(f"Created {len(chunks)} chunks for ticket {ticket.key}")
        return chunks
    
    def process_ticket_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single JIRA ticket file
        
        Args:
            file_path: Path to ticket file
            
        Returns:
            Processing results
        """
        try:
            logger.info(f"Processing JIRA ticket file: {file_path}")
            
            # Parse tickets from file
            tickets = self.parse_ticket_file(file_path)
            
            if not tickets:
                logger.warning(f"No tickets found in file: {file_path}")
                return {
                    "file_path": file_path,
                    "status": "skipped",
                    "reason": "no_tickets",
                    "tickets_processed": 0,
                    "chunks_created": 0
                }
            
            all_chunks = []
            successful_tickets = 0
            
            # Process each ticket
            for ticket in tickets:
                try:
                    ticket_chunks = self.create_ticket_chunks(ticket)
                    all_chunks.extend(ticket_chunks)
                    successful_tickets += 1
                    logger.debug(f"Processed ticket {ticket.key}: {len(ticket_chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error processing ticket {ticket.key}: {e}")
            
            if not all_chunks:
                logger.warning(f"No chunks created from file: {file_path}")
                return {
                    "file_path": file_path,
                    "status": "skipped",
                    "reason": "no_chunks",
                    "tickets_processed": successful_tickets,
                    "chunks_created": 0
                }
            
            # Generate embeddings
            texts = [chunk.text for chunk in all_chunks]
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.embedding_service.get_embeddings(texts)
            
            # Store in Qdrant
            points = []
            for chunk, embedding in zip(all_chunks, embeddings):
                point_id = hashlib.md5(f"{chunk.metadata['chunk_id']}".encode()).hexdigest()
                
                points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "chunk_text": chunk.text,
                        **chunk.metadata
                    }
                })
            
            # Ensure collection exists
            self.qdrant_service.create_collection(
                collection_name=self.collection_name,
                vector_dimension=self.embedding_service.get_dimension()
            )
            
            # Store points
            self.qdrant_service.store_vectors(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"✅ Successfully processed JIRA file: {Path(file_path).name}")
            logger.info(f"   Processed {successful_tickets} tickets")
            logger.info(f"   Created {len(all_chunks)} chunks")
            logger.info(f"   Stored in collection: {self.collection_name}")
            
            return {
                "file_path": file_path,
                "status": "success",
                "tickets_processed": successful_tickets,
                "chunks_created": len(all_chunks),
                "collection_name": self.collection_name,
                "embeddings_generated": len(embeddings)
            }
            
        except Exception as e:
            logger.error(f"Error processing JIRA file {file_path}: {e}")
            return {
                "file_path": file_path,
                "status": "error",
                "error": str(e),
                "tickets_processed": 0,
                "chunks_created": 0
            }
    
    def process_all_tickets(self) -> List[Dict[str, Any]]:
        """
        Process all JIRA ticket files in the documents directory
        
        Returns:
            List of processing results
        """
        # Look for various ticket file formats
        ticket_files = []
        for pattern in ["*.txt", "*.json", "*.csv"]:
            ticket_files.extend(self.documents_path.glob(pattern))
        
        if not ticket_files:
            logger.warning(f"No ticket files found in {self.documents_path}")
            return []
        
        logger.info(f"Found {len(ticket_files)} ticket files to process")
        results = []
        
        for ticket_file in ticket_files:
            try:
                result = self.process_ticket_file(str(ticket_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {ticket_file}: {e}")
                results.append({
                    "file_path": str(ticket_file),
                    "status": "error",
                    "error": str(e),
                    "tickets_processed": 0,
                    "chunks_created": 0
                })
        
        # Summary
        successful = len([r for r in results if r["status"] == "success"])
        total_tickets = sum(r.get("tickets_processed", 0) for r in results)
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        
        logger.info(f"JIRA Processing Summary:")
        logger.info(f"  Files processed: {successful}/{len(ticket_files)}")
        logger.info(f"  Total tickets processed: {total_tickets}")
        logger.info(f"  Total chunks created: {total_chunks}")
        logger.info(f"  Collection: {self.collection_name}")
        
        return results


def create_jira_processor(embedding_service, qdrant_service) -> JIRATicketProcessor:
    """
    Factory function to create JIRA ticket processor
    
    Args:
    embedding_service: BGE embedding service instance
        qdrant_service: Qdrant service instance
        
    Returns:
        Configured JIRA ticket processor
    """
    return JIRATicketProcessor(
        embedding_service=embedding_service,
        qdrant_service=qdrant_service
    )


if __name__ == "__main__":
    # Test the JIRA processor
    from embedding_bge_service import create_bge_embedding_service
    from jira_qdrant_service import JiraQdrantService
    
    # Load environment
    import sys
    sys.path.append('/home/ubuntu/Ravi/ComBot/backend/langgraph')
    
    def load_env():
        env_path = "/home/ubuntu/Ravi/ComBot/.env"
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value.strip('"\'')
    
    load_env()
    
    # Initialize services
    embedding_service = create_bge_embedding_service()
    qdrant_service = JiraQdrantService()
    
    # Create and test processor
    processor = create_jira_processor(embedding_service, qdrant_service)
    
    print("🔍 Looking for JIRA ticket files...")
    doc_path = Path("/home/ubuntu/Ravi/ComBot/backend/documents/")
    ticket_files = list(doc_path.glob("*.txt")) + list(doc_path.glob("*.json"))
    print(f"Found {len(ticket_files)} ticket files")
    
    if ticket_files:
        # Process first file as test
        result = processor.process_ticket_file(str(ticket_files[0]))
        print(f"Test result: {result}")
    else:
        print("No ticket files found to test")