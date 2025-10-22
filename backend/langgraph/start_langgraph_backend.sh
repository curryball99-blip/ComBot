#!/bin/bash
"""
🚀 LangGraph Backend Startup Script
==================================

This script starts the new LangGraph-based dual document processing backend.
Processes JIRA tickets and PDF documents using BGE embeddings (BAAI/bge-large-en-v1.5) exclusively.
"""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting LangGraph Backend System${NC}"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "langgraph_workflow.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the backend/langgraph directory${NC}"
    exit 1
fi

# Load environment variables
echo -e "${YELLOW}🔧 Loading environment variables...${NC}"
if [ -f "../../.env" ]; then
    set -o allexport
    source ../../.env
    set +o allexport
    echo -e "${GREEN}✅ Environment loaded${NC}"
else
    echo -e "${RED}❌ Error: .env file not found${NC}"
    exit 1
fi

# Check Docker containers
echo -e "${YELLOW}🐳 Checking Docker services...${NC}"

# Check Redis
if docker ps | grep -q "redis.*Up"; then
    echo -e "${GREEN}✅ Redis container is running${NC}"
else
    echo -e "${YELLOW}🔄 Starting Redis container...${NC}"
    docker start redis || docker run -d -p 6379:6379 --name redis redis:latest
fi

# Check Qdrant
if docker ps | grep -q "qdrant.*Up"; then
    echo -e "${GREEN}✅ Qdrant container is running${NC}"
else
    echo -e "${YELLOW}🔄 Starting Qdrant container...${NC}"
    docker start qdrant || docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
fi

# Check HuggingFace token
if [ -z "$HF_API_TOKEN" ]; then
    echo -e "${RED}❌ Error: HF_API_TOKEN not found in environment${NC}"
    exit 1
else
    echo -e "${GREEN}✅ HuggingFace token loaded${NC}"
fi

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 3

echo -e "${GREEN}🎉 LangGraph Backend is ready!${NC}"
echo ""
echo -e "${BLUE}📋 Available Commands:${NC}"
echo "1. Process documents: python process_documents.py"
echo "2. Start interactive processing: python langgraph_interactive.py"
echo "3. Run tests: python test_with_env.py"
echo "4. Process specific file: python process_specific.py <file_path>"
echo ""
echo -e "${BLUE}📁 Document Directories:${NC}"
echo "- PDF documents: /home/ubuntu/Ravi/ComBot/uploads/"
echo "- JIRA documents: /home/ubuntu/Ravi/ComBot/backend/documents/"
echo ""
echo -e "${BLUE}🔗 Service URLs:${NC}"
echo "- Qdrant Web UI: http://localhost:6333/dashboard"
echo "- Redis: localhost:6379"
echo ""
echo -e "${GREEN}✨ LangGraph Backend Started Successfully!${NC}"