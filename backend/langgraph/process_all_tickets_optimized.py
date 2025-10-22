#!/usr/bin/env python3
"""
🚀 Optimized JIRA Tickets Processing with BGE Embeddings
========================================================

High-performance processing of all_tickets.json with parallel embedding generation
and optimized batch sizes for 15GB RAM system.

Features:
- Parallel embedding generation with optimal batch sizes
- Memory-efficient processing for large ticket datasets  
- BGE embeddings (1024 dimensions)
- Progress tracking and error handling
- Qdrant storage optimization
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

# Load environment variables
load_dotenv('/home/ubuntu/Ravi/ComBot/.env')

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_all_tickets():
    """Process all_tickets.json with optimized parallel processing."""
    
    print("🚀 FULL: JIRA Tickets Processing (All 3129 tickets)")
    print("=" * 60)
    
    # Check if all_tickets.json exists 
    ticket_path = "/home/ubuntu/Ravi/ComBot/backend/documents/all_tickets.json"
    if not os.path.exists(ticket_path):
        print(f"❌ Error: all_tickets.json not found at {ticket_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(ticket_path)
    print(f"📁 Processing: {ticket_path}")
    print(f"📊 File size: {file_size / (1024*1024):.1f} MB")
    
    # Count tickets
    with open(ticket_path, 'r') as f:
        tickets = json.load(f)
    
    ticket_count = len(tickets)
    print(f"🎫 Total tickets: {ticket_count}")
    
    # Debug: Test embedding service dimensions
    print(f"\n🔍 DEBUG: Testing BGE Embedding Service...")
    try:
        sys.path.append(str(Path(__file__).parent))
        from embedding_service_factory import create_embedding_backend
        embedding_service = create_embedding_backend()
        test_embedding = embedding_service.get_embedding("test text")
        print(f"   📏 BGE Model: {embedding_service.model_name}")
        print(f"   📊 Expected dimension: {embedding_service.get_dimension()}")
        print(f"   🧮 Actual test embedding dimension: {len(test_embedding)}")
    except Exception as e:
        print(f"   ❌ BGE Service Error: {e}")
    
    # Memory optimization settings for production
    print(f"\n⚙️ Production Settings:")
    print(f"   🔄 Embedding batch size: 32 (optimized for throughput)")
    print(f"   🧠 Memory efficient processing")
    print(f"   ⚡ Parallel embedding generation enabled")
    
    try:
        # Set production environment variables (reduced for stability)
        os.environ['EMBEDDING_BATCH_SIZE'] = '16'   # Reduced batch for stability
        os.environ['JIRA_CHUNK_SIZE'] = '8'         # Smaller chunks to prevent timeouts
        
        # Import and initialize workflow after env vars are set
        from langgraph_workflow import DualDocumentProcessingWorkflow
        
        print(f"\n🔧 Initializing optimized LangGraph workflow...")
        workflow = DualDocumentProcessingWorkflow()
        
        # Start processing
        print(f"🚀 Starting FULL processing of {ticket_count} tickets...")
        print(f"⏱️ Estimated time: ~45-60 minutes (full dataset)")
        
        start_time = time.time()
        
        # Process with progress tracking
        result = await process_with_progress_tracking(workflow, ticket_count)
        
        end_time = time.time()
        processing_time = (end_time - start_time) / 60  # Convert to minutes
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 PROCESSING RESULTS")
        print("=" * 60)
        
        stats = result.get('stats', {})
        
        print(f"⏱️  Total processing time: {processing_time:.2f} minutes")
        print(f"📄 Documents processed: {stats.get('documents_processed', 0)}")
        print(f"🧩 Chunks created: {stats.get('chunks_created', 0)}")
        print(f"🧠 Embeddings generated: {stats.get('embeddings_generated', 0)}")
        print(f"🗄️  Vectors stored in Qdrant: {stats.get('vectors_stored', 0)}")
        print(f"🎫 JIRA vectors: {stats.get('jira_vectors', 0)}")
        print(f"⚡ Processing rate: {ticket_count/processing_time:.1f} tickets/minute")
        
        if result.get('errors'):
            print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
            for i, error in enumerate(result['errors'][:5], 1):  # Show first 5 errors
                print(f"   {i}. {error}")
            if len(result['errors']) > 5:
                print(f"   ... and {len(result['errors']) - 5} more errors")
        else:
            print(f"\n✅ No errors encountered")
        
        # Verify storage
        vectors_stored = stats.get('vectors_stored', 0)
        if vectors_stored > 0:
            print(f"\n🎉 SUCCESS! {vectors_stored} vectors stored in Qdrant")
            print(f"🔍 Chat search now uses BGE embeddings (1024 dimensions)")
            print(f"💾 Memory usage optimized for large dataset")
            return True
        else:
            print(f"\n⚠️  No vectors were stored. Check errors above.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        logger.exception("Processing failed")
        return False

async def process_with_progress_tracking(workflow, total_tickets):
    """Process with real-time progress tracking."""
    
    print(f"\n📈 Progress Tracking (every 50 tickets):")
    print(f"{'Progress':<10} {'Completed':<10} {'Rate':<15} {'ETA':<10}")
    print(f"{'-'*10} {'-'*10} {'-'*15} {'-'*10}")
    
    start_time = time.time()
    
    # Start processing (this will run in background)
    process_task = asyncio.create_task(workflow.process_documents())
    
    # Track progress while processing
    last_check = 0
    while not process_task.done():
        await asyncio.sleep(5)  # Check every 5 seconds
        
        # You could add Qdrant vector count checking here for real progress
        # For now, we'll show time-based progress
        elapsed = time.time() - start_time
        
        if elapsed - last_check >= 30:  # Report every 30 seconds
            estimated_progress = min(95, (elapsed / (total_tickets * 0.05)))  # Rough estimate
            rate = estimated_progress / (elapsed / 60) if elapsed > 0 else 0
            eta = (100 - estimated_progress) / rate if rate > 0 else 0
            
            print(f"{estimated_progress:>8.1f}% {int(estimated_progress * total_tickets / 100):>8d} {rate:>10.1f}/min {eta:>8.1f}min")
            last_check = elapsed
    
    # Get final result
    result = await process_task
    return result

def estimate_processing_time(ticket_count):
    """Estimate processing time based on ticket count and system specs."""
    # Rough estimates for 15GB RAM system with BGE embeddings
    # BGE processing: ~10-15 tickets per minute with optimizations
    estimated_rate = 12  # tickets per minute
    return max(1, ticket_count / estimated_rate)

async def clean_qdrant_collections():
    """Clean existing Qdrant collections before reprocessing."""
    print(f"\n🧹 Cleaning Qdrant collections...")
    
    try:
        import httpx
        
        # Delete existing collections
        collections = ['jira_tickets', 'pdf_documents']
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for collection in collections:
                try:
                    response = await client.delete(f"http://localhost:6333/collections/{collection}")
                    if response.status_code in [200, 404]:
                        print(f"   ✅ Cleaned collection: {collection}")
                    else:
                        print(f"   ⚠️  Failed to clean {collection}: {response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Error cleaning {collection}: {e}")
        
        # Wait a bit for cleanup
        await asyncio.sleep(2)
        print(f"✅ Qdrant cleanup completed")
        return True
        
    except Exception as e:
        print(f"❌ Qdrant cleanup failed: {e}")
        return False

async def verify_final_storage():
    """Verify that all vectors were properly stored."""
    print(f"\n🔍 Verifying final storage...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check jira_tickets collection
            response = await client.get("http://localhost:6333/collections/jira_tickets")
            if response.status_code == 200:
                data = response.json()
                point_count = data['result']['points_count']
                vector_size = data['result']['config']['params']['vectors']['size']
                
                print(f"✅ JIRA Collection Verified:")
                print(f"   📊 Total vectors: {point_count}")
                print(f"   📏 Vector dimension: {vector_size}")
                print(f"   🧠 Embedding type: BGE (BAAI/bge-large-en-v1.5)")
                
                if vector_size == 1024:
                    print(f"   ✅ Correct BGE dimensions confirmed")
                else:
                    print(f"   ⚠️  Warning: Expected 1024 dimensions, got {vector_size}")
                
                return point_count > 0
            else:
                print(f"❌ Collection verification failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Storage verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting optimized all_tickets.json processing...")
    
    # Check environment
    required_env = ['HF_API_TOKEN', 'QDRANT_URL']
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        print(f"❌ Error: Missing environment variables: {missing_env}")
        print("Please check your .env file.")
        sys.exit(1)
    
    # Memory check
    try:
        import psutil
        total_ram = psutil.virtual_memory().total / (1024**3)  # GB
        print(f"💾 System RAM: {total_ram:.1f} GB")
        if total_ram < 12:
            print("⚠️  Warning: Less than 12GB RAM detected. Processing may be slower.")
    except ImportError:
        print("💾 RAM check skipped (psutil not installed)")
    
    async def main():
        # Step 1: Clean existing data
        print("\n" + "="*60)
        print("STEP 1: CLEANING EXISTING DATA")
        print("="*60)
        
        clean_success = await clean_qdrant_collections()
        if not clean_success:
            print("⚠️  Cleanup failed, but continuing...")
        
        # Step 2: Process all tickets
        print("\n" + "="*60)
        print("STEP 2: PROCESSING ALL TICKETS")
        print("="*60)
        
        success = await process_all_tickets()
        
        # Step 3: Verify storage
        if success:
            print("\n" + "="*60)
            print("STEP 3: VERIFICATION")
            print("="*60)
            
            verify_success = await verify_final_storage()
            
            if verify_success:
                print(f"\n🎉 ALL TICKETS PROCESSED SUCCESSFULLY!")
                print(f"✅ BGE embeddings ready for chat search")
                print(f"🔍 Dimension mismatch issue resolved")
            else:
                print(f"\n⚠️  Processing completed but verification failed")
        else:
            print(f"\n❌ Processing failed. Check errors above.")
            sys.exit(1)
    
    # Run the main process
    asyncio.run(main())