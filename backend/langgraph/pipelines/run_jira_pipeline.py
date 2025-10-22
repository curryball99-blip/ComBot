"""
JIRA Ticket Processing Pipeline Runner        # Create embedding service with auto-detection
        service = create_embedding_service(model_type="auto")===============================

Main script to run the JIRA ticket processing pipeline with LangGraph
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from pipelines.jira_processor import JiraTicketProcessor, load_tickets_from_file
# Legacy Gemma embedding removed; using unified BGE factory
from embedding_service_factory import create_embedding_backend
from ..jira_qdrant_service import JiraQdrantService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the JIRA processing pipeline"""
    
    # Configuration
    TICKETS_FILE = "/home/ubuntu/Ravi/ComBot/backend/documents/Tic10.txt"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    try:
        logger.info("=== Starting JIRA Ticket Processing Pipeline ===")
        
        # 1. Initialize services
        logger.info("Initializing services...")
        
        # Create embedding service (BGE)
        embedding_service = create_embedding_backend()
        
        # Create Qdrant service
        qdrant_service = JiraQdrantService()
        await qdrant_service.initialize()
        
        # 2. Load JIRA tickets
        logger.info(f"Loading tickets from: {TICKETS_FILE}")
        tickets_data = load_tickets_from_file(TICKETS_FILE)
        
        if not tickets_data:
            logger.error("No tickets loaded. Exiting.")
            return
            
        logger.info(f"Loaded {len(tickets_data)} tickets")
        
        # 3. Initialize processor
        processor = JiraTicketProcessor(
            embedding_service=embedding_service,
            qdrant_service=qdrant_service,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        
        # 4. Process tickets
        logger.info("Starting ticket processing...")
        final_state = await processor.process_tickets(tickets_data)
        
        # 5. Report results
        logger.info("=== Processing Complete ===")
        logger.info(f"Successfully processed: {len(final_state.processed_tickets)} tickets")
        logger.info(f"Total chunks created: {len(final_state.ticket_chunks)}")
        logger.info(f"Total chunks embedded: {len(final_state.embedded_chunks)}")
        logger.info(f"Total chunks stored: {len(final_state.stored_chunks)}")
        
        if final_state.errors:
            logger.warning(f"Errors encountered: {len(final_state.errors)}")
            for error in final_state.errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("✅ All tickets processed successfully!")
        
        # 6. Show processed ticket summary
        logger.info("\n=== Processed Tickets Summary ===")
        for ticket in final_state.processed_tickets:
            ticket_chunks = [c for c in final_state.ticket_chunks if c.ticket_key == ticket.ticket_key]
            logger.info(f"📋 {ticket.ticket_key}: {ticket.summary[:60]}...")
            logger.info(f"   Status: {ticket.status} | Priority: {ticket.priority}")
            logger.info(f"   Components: {', '.join(ticket.components)}")
            logger.info(f"   Chunks: {len(ticket_chunks)} | Comments: {ticket.comment_count}")
            logger.info("")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


async def test_individual_ticket():
    """Test processing with a single ticket for debugging"""
    
    TICKETS_FILE = "/home/ubuntu/Ravi/ComBot/backend/documents/Tic10.txt"
    
    try:
        # Load just first ticket
        all_tickets = load_tickets_from_file(TICKETS_FILE)
        if not all_tickets:
            logger.error("No tickets found")
            return
            
        # Take first ticket only
        test_tickets = [all_tickets[0]]
        
        logger.info(f"Testing with single ticket: {test_tickets[0].get('key', 'Unknown')}")
        
        # Initialize services
    embedding_service = create_embedding_backend()
        qdrant_service = JiraQdrantService()
        await qdrant_service.initialize()
        
        # Process
        processor = JiraTicketProcessor(
            embedding_service=embedding_service,
            qdrant_service=qdrant_service,
            chunk_size=500,  # Smaller chunks for testing
            chunk_overlap=100
        )
        
        final_state = await processor.process_tickets(test_tickets)
        
        # Results
        logger.info(f"Test completed!")
        logger.info(f"Chunks: {len(final_state.ticket_chunks)}")
        logger.info(f"Embedded: {len(final_state.embedded_chunks)}")
        logger.info(f"Stored: {len(final_state.stored_chunks)}")
        
        if final_state.errors:
            for error in final_state.errors:
                logger.error(f"Error: {error}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


async def search_tickets(query: str):
    """Test searching processed tickets"""
    
    try:
        # Initialize services
        embedding_service = create_embedding_service(model_type="gemma")
        qdrant_service = JiraQdrantService()
        await qdrant_service.initialize()
        
        # Search in all ticket collections
        # (In a real implementation, you'd want to search across all collections)
        logger.info(f"Searching for: '{query}'")
        
        # For now, just test the embedding service
        test_texts = [
            "ELK shards limit exceeded causing index creation failure",
            "Binary message delivery issue in MO-AT flow",
            "Error code 602/702 instead of actual failure reasons",
            "Attachment missing for A2P and P2P spike analysis"
        ]
        
        results = await embedding_service.similarity_search(query, test_texts, top_k=3)
        
        logger.info("Search results:")
        for text, score, idx in results:
            logger.info(f"  {score:.3f}: {text}")
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JIRA Ticket Processing Pipeline")
    parser.add_argument("--mode", choices=["full", "test", "search"], default="full",
                       help="Processing mode")
    parser.add_argument("--query", type=str, help="Search query (for search mode)")
    
    args = parser.parse_args()
    
    if args.mode == "full":
        asyncio.run(main())
    elif args.mode == "test":
        asyncio.run(test_individual_ticket())
    elif args.mode == "search":
        if not args.query:
            print("Please provide a query with --query")
            sys.exit(1)
        asyncio.run(search_tickets(args.query))