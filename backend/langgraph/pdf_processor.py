"""
PDF Document Processor using PyMuPDF
===================================

Processes PDF documents from /home/ubuntu/Ravi/ComBot/uploads/
- Uses PyMuPDF for PDF parsing and text extraction
- Uses BGE embeddings (BAAI/bge-large-en-v1.5, 1024-d)
- Stores in shared Qdrant database with collection: pdf_documents
"""

import os
import logging
import hashlib
import re
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
from dataclasses import dataclass
from datetime import datetime
import psutil
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PDFChunk:
    """Represents a chunk of text from a PDF document"""
    text: str
    page_number: int
    chunk_index: int
    document_name: str
    file_path: str
    metadata: Dict[str, Any]

class PDFProcessor:
    """
    Advanced PDF document processor using PyMuPDF for parsing and BGE embeddings (1024-d)
    Features:
    - Intelligent semantic chunking
    - Content analysis and categorization
    - Dynamic chunk sizing
    - Optimized batch processing
    - Enhanced metadata extraction
    """
    
    def __init__(self, 
                 embedding_service,
                 qdrant_service,
                 uploads_path: str = "/home/ubuntu/Ravi/ComBot/uploads/",
                 base_chunk_size: int = 1200,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 200):
        """
        Initialize advanced PDF processor
        
        Args:
            embedding_service: BGE embedding service instance
            qdrant_service: Qdrant service for vector storage
            uploads_path: Path to PDF files
            base_chunk_size: Base size for text chunks (adaptive)
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size threshold
        """
        self.embedding_service = embedding_service
        self.qdrant_service = qdrant_service
        self.uploads_path = Path(uploads_path)
        self.base_chunk_size = base_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.collection_name = "pdf_documents"
        
        # Optimization parameters from existing backend
        cpu_cores = psutil.cpu_count(logical=False) or 4
        self.max_workers = min(cpu_cores, 8)
        
        # Dynamic batch sizes based on available memory
        available_memory = psutil.virtual_memory().available / 1024**3
        if available_memory > 32:
            self.embedding_batch_size = 128
        elif available_memory > 16:
            self.embedding_batch_size = 96
        else:
            self.embedding_batch_size = 64
        
        # Thread executor for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        logger.info(f"Initialized advanced PDF processor for: {self.uploads_path}")
        logger.info(f"Base chunk size: {base_chunk_size}, Overlap: {chunk_overlap}")
        logger.info(f"Workers: {self.max_workers}, Batch size: {self.embedding_batch_size}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF using PyMuPDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page data with text and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            logger.info(f"Extracting text from PDF: {pdf_path}")
            logger.info(f"Document has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text
                text = page.get_text()
                
                # Get page metadata
                page_metadata = {
                    "page_number": page_num + 1,
                    "page_width": page.rect.width,
                    "page_height": page.rect.height,
                    "rotation": page.rotation
                }
                
                # Extract images info
                images = page.get_images()
                page_metadata["image_count"] = len(images)
                
                pages_data.append({
                    "page_number": page_num + 1,
                    "text": text.strip(),
                    "metadata": page_metadata
                })
                
                logger.debug(f"Page {page_num + 1}: {len(text)} characters extracted")
            
            # Get document metadata
            doc_metadata = doc.metadata
            doc.close()
            
            # Add document-level metadata to all pages
            for page_data in pages_data:
                page_data["document_metadata"] = doc_metadata
            
            logger.info(f"Successfully extracted text from {len(pages_data)} pages")
            return pages_data
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise
    
    def _chunk_text_intelligently(self, text: str, page_number: int = None, document_name: str = None) -> List[Dict[str, Any]]:
        """
        Intelligent chunking that preserves semantic coherence
        Adapted from document_processor_optimized.py
        """
        if len(text) <= self.base_chunk_size:
            return [{
                "text": text, 
                "chunk_type": "complete",
                "page_number": page_number,
                "document_name": document_name
            }]
        
        chunks = []
        
        # First, try to split by paragraphs for better semantic coherence
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = ""
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            para_size = len(paragraph)
            
            # If paragraph alone is too big, split it further
            if para_size > self.base_chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_type": "paragraph_group",
                        "page_number": page_number,
                        "document_name": document_name
                    })
                    current_chunk = ""
                    current_size = 0
                
                # Split large paragraph by sentences
                sentence_chunks = self._split_large_paragraph(paragraph, page_number, document_name)
                chunks.extend(sentence_chunks)
                
            elif current_size + para_size + 1 <= self.base_chunk_size:
                # Add paragraph to current chunk
                current_chunk += paragraph + "\n\n"
                current_size += para_size + 2
                
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_type": "paragraph_group",
                        "page_number": page_number,
                        "document_name": document_name
                    })
                
                current_chunk = paragraph + "\n\n"
                current_size = para_size + 2
        
        # Add final chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_type": "paragraph_group",
                "page_number": page_number,
                "document_name": document_name
            })
        
        # Filter out chunks that are too small
        valid_chunks = [
            chunk for chunk in chunks 
            if len(chunk["text"]) >= self.min_chunk_size
        ]
        
        logger.debug(f"Intelligent chunking: {len(valid_chunks)} semantic chunks created for page {page_number}")
        return valid_chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs while preserving structure"""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean up paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 20:  # Minimum paragraph length
                cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs
    
    def _split_large_paragraph(self, paragraph: str, page_number: int = None, document_name: str = None) -> List[Dict[str, Any]]:
        """Split large paragraphs by sentences while maintaining context"""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 1 <= self.base_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_type": "sentence_group",
                        "page_number": page_number,
                        "document_name": document_name
                    })
                current_chunk = sentence + " "
        
        # Add final chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_type": "sentence_group",
                "page_number": page_number,
                "document_name": document_name
            })
        
        return chunks
    
    def _detect_language_simple(self, text: str) -> str:
        """Simple language detection based on character patterns"""
        # Basic heuristic for English vs other languages
        english_words = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use']
        
        words = text.lower().split()[:100]  # Check first 100 words
        english_count = sum(1 for word in words if word in english_words)
        
        if len(words) > 0 and english_count / len(words) > 0.1:
            return 'en'
        else:
            return 'unknown'
    
    def _categorize_content(self, text: str) -> str:
        """Categorize content based on keywords and patterns"""
        text_lower = text.lower()
        
        # Technical document indicators  
        technical_keywords = ['algorithm', 'implementation', 'function', 'method', 'class', 'variable', 'database', 'api', 'server', 'client', 'protocol', 'framework', 'library', 'documentation']
        
        # Business document indicators
        business_keywords = ['revenue', 'profit', 'market', 'customer', 'strategy', 'analysis', 'report', 'budget', 'financial', 'sales', 'marketing', 'business', 'company', 'organization']
        
        # Research/Academic indicators
        research_keywords = ['study', 'research', 'analysis', 'methodology', 'results', 'conclusion', 'abstract', 'hypothesis', 'experiment', 'survey', 'literature', 'academic', 'journal', 'publication']
        
        # Legal document indicators
        legal_keywords = ['contract', 'agreement', 'legal', 'law', 'clause', 'terms', 'conditions', 'liability', 'compliance', 'regulation', 'policy', 'rights', 'obligations']
        
        # Count keyword occurrences
        categories = {
            'technical': sum(1 for keyword in technical_keywords if keyword in text_lower),
            'business': sum(1 for keyword in business_keywords if keyword in text_lower),
            'research': sum(1 for keyword in research_keywords if keyword in text_lower),
            'legal': sum(1 for keyword in legal_keywords if keyword in text_lower)
        }
        
        # Return category with highest count, or 'general' if none significant
        max_category = max(categories, key=categories.get)
        if categories[max_category] > 2:  # At least 3 relevant keywords
            return max_category
        else:
            return 'general'
    
    def chunk_text(self, text: str, page_number: int, document_name: str = None) -> List[Dict[str, Any]]:
        """
        Intelligent text chunking with semantic coherence
        
        Args:
            text: Text to chunk
            page_number: Page number for context
            document_name: Document name for metadata
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not text.strip():
            return []
        
        # Use intelligent chunking method
        chunks = self._chunk_text_intelligently(text, page_number, document_name)
        
        logger.debug(f"Page {page_number}: Created {len(chunks)} intelligent chunks")
        return chunks
    
    def create_pdf_chunks(self, pdf_path: str) -> List[PDFChunk]:
        """
        Create intelligent chunks from PDF with enhanced metadata and content analysis
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PDF chunks with enhanced metadata
        """
        document_name = Path(pdf_path).stem
        pages_data = self.extract_text_from_pdf(pdf_path)
        
        pdf_chunks = []
        
        # Combine all text for document-level analysis
        full_text = " ".join([page["text"] for page in pages_data if page["text"].strip()])
        
        # Document-level content analysis
        content_language = self._detect_language_simple(full_text)
        content_category = self._categorize_content(full_text)
        
        # Calculate document hash for deduplication
        doc_hash = hashlib.md5(full_text.encode()).hexdigest()
        
        logger.info(f"Document analysis - Language: {content_language}, Category: {content_category}")
        
        for page_data in pages_data:
            page_number = page_data["page_number"]
            text = page_data["text"]
            
            if not text.strip():
                logger.debug(f"Skipping empty page {page_number}")
                continue
            
            # Use intelligent chunking
            chunk_dicts = self.chunk_text(text, page_number, document_name)
            
            for chunk_index, chunk_dict in enumerate(chunk_dicts):
                chunk_text = chunk_dict["text"]
                chunk_type = chunk_dict.get("chunk_type", "standard")
                
                # Enhanced metadata with content analysis
                chunk_metadata = {
                    "document_name": document_name,
                    "file_path": str(pdf_path),
                    "document_hash": doc_hash,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "chunk_id": f"{document_name}_p{page_number}_c{chunk_index}",
                    "chunk_type": chunk_type,
                    "content_type": "pdf",
                    "content_language": content_language,
                    "content_category": content_category,
                    "processed_at": datetime.now().isoformat(),
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                    "content_preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                    **page_data["metadata"],
                    **page_data.get("document_metadata", {})
                }
                
                pdf_chunk = PDFChunk(
                    text=chunk_text,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    document_name=document_name,
                    file_path=str(pdf_path),
                    metadata=chunk_metadata
                )
                
                pdf_chunks.append(pdf_chunk)
        
        logger.info(f"Created {len(pdf_chunks)} intelligent chunks from PDF: {document_name}")
        logger.info(f"Chunk types: {list(set(chunk.metadata['chunk_type'] for chunk in pdf_chunks))}")
        return pdf_chunks
    
    async def process_pdf_file(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a single PDF file with optimized batch processing
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Processing results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Processing PDF file: {pdf_path}")
            
            # Extract and create chunks (CPU-bound, run in executor)
            pdf_chunks = await self._run_in_executor(self.create_pdf_chunks, pdf_path)
            
            if not pdf_chunks:
                logger.warning(f"No chunks created from PDF: {pdf_path}")
                return {
                    "file_path": pdf_path,
                    "status": "skipped",
                    "reason": "no_content",
                    "chunks_created": 0
                }
            
            # Generate embeddings in optimized batches
            total_chunks = len(pdf_chunks)
            texts = [chunk.text for chunk in pdf_chunks]
            
            logger.info(f"Generating embeddings for {total_chunks} chunks in batches of {self.embedding_batch_size}...")
            
            all_embeddings = []
            
            # Process embeddings in batches
            for i in range(0, total_chunks, self.embedding_batch_size):
                batch_end = min(i + self.embedding_batch_size, total_chunks)
                batch_texts = texts[i:batch_end]
                
                # Generate embeddings for batch
                batch_embeddings = await self.embedding_service.get_embeddings_batch_async(batch_texts)
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Processed embedding batch {i//self.embedding_batch_size + 1}/{(total_chunks-1)//self.embedding_batch_size + 1}")
                
                # Yield control to prevent blocking
                await asyncio.sleep(0.01)
            
            # Prepare documents for storage
            documents_to_add = []
            for chunk, embedding in zip(pdf_chunks, all_embeddings):
                documents_to_add.append({
                    "text": chunk.text,
                    "embedding": embedding,
                    "metadata": chunk.metadata
                })
            
            # Store in Qdrant using optimized batch operations
            await self.qdrant_service.ensure_collection_exists_async(
                collection_name=self.collection_name,
                vector_size=self.embedding_service.get_dimension()
            )
            
            point_ids = await self.qdrant_service.add_documents_batch_async(documents_to_add)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Successfully processed PDF: {Path(pdf_path).name} in {processing_time:.2f}s")
            logger.info(f"   Created {len(pdf_chunks)} intelligent chunks")
            logger.info(f"   Generated {len(all_embeddings)} embeddings")
            logger.info(f"   Stored {len(point_ids)} vectors in collection: {self.collection_name}")
            
            return {
                "file_path": pdf_path,
                "document_name": Path(pdf_path).stem,
                "status": "success",
                "chunks_created": len(pdf_chunks),
                "collection_name": self.collection_name,
                "embeddings_generated": len(all_embeddings),
                "processing_time": processing_time,
                "chunk_types": list(set(chunk.metadata['chunk_type'] for chunk in pdf_chunks))
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error processing PDF {pdf_path} after {processing_time:.2f}s: {e}")
            return {
                "file_path": pdf_path,
                "status": "error",
                "error": str(e),
                "chunks_created": 0,
                "processing_time": processing_time
            }
    
    async def _run_in_executor(self, func, *args):
        """Run CPU-bound operations in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)
    
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """
        Process all PDF files in the uploads directory
        
        Returns:
            List of processing results
        """
        pdf_files = list(self.uploads_path.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.uploads_path}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        results = []
        
        for pdf_file in pdf_files:
            try:
                result = self.process_pdf_file(str(pdf_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                results.append({
                    "file_path": str(pdf_file),
                    "status": "error",
                    "error": str(e),
                    "chunks_created": 0
                })
        
        # Summary
        successful = len([r for r in results if r["status"] == "success"])
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        
        logger.info(f"PDF Processing Summary:")
        logger.info(f"  Files processed: {successful}/{len(pdf_files)}")
        logger.info(f"  Total chunks created: {total_chunks}")
        logger.info(f"  Collection: {self.collection_name}")
        
        return results


def create_pdf_processor(embedding_service, qdrant_service) -> PDFProcessor:
    """
    Factory function to create PDF processor
    
    Args:
    embedding_service: BGE embedding service instance
        qdrant_service: Qdrant service instance
        
    Returns:
        Configured PDF processor
    """
    return PDFProcessor(
        embedding_service=embedding_service,
        qdrant_service=qdrant_service
    )


if __name__ == "__main__":
    # Test the PDF processor
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
    processor = create_pdf_processor(embedding_service, qdrant_service)
    
    print("🔍 Looking for PDF files...")
    pdf_files = list(Path("/home/ubuntu/Ravi/ComBot/uploads/").glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    if pdf_files:
        # Process first PDF as test
        result = processor.process_pdf_file(str(pdf_files[0]))
        print(f"Test result: {result}")
    else:
        print("No PDF files found to test")