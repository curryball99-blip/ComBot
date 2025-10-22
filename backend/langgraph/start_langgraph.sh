#!/bin/bash

# LangGraph Backend Startup Script
# ================================

echo "🚀 Starting LangGraph Backend Server..."

# Check if we're in the right directory
if [ ! -f "app_langgraph.py" ]; then
    echo "❌ Error: app_langgraph.py not found. Please run from the backend/langgraph directory."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected. Attempting to activate clean_rag_venv..."
    if [ -d "../../clean_rag_venv" ]; then
        source ../../clean_rag_venv/bin/activate
        echo "✅ Activated clean_rag_venv"
    else
        echo "❌ Error: Virtual environment not found. Please activate your Python environment."
        exit 1
    fi
fi

# Check required environment variables
echo "🔧 Checking environment variables..."

if [ -z "$HUGGINGFACE_TOKEN" ]; then
    echo "⚠️  Warning: HUGGINGFACE_TOKEN not set. BGE model download may fail."
fi

if [ -z "$JIRA_URL" ] || [ -z "$JIRA_USERNAME" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo "⚠️  Warning: JIRA credentials not configured. JIRA dashboard will be disabled."
fi

# Check if Docker services are running
echo "🐳 Checking Docker services..."

if ! docker ps | grep -q "qdrant/qdrant"; then
    echo "⚠️  Warning: Qdrant container not found. Starting Qdrant..."
    docker run -d --name qdrant-langgraph -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
fi

if ! docker ps | grep -q "redis"; then
    echo "⚠️  Warning: Redis container not found. Starting Redis..."
    docker run -d --name redis-langgraph -p 6379:6379 redis:alpine
fi

echo "✅ Docker services check complete"

# Install dependencies if needed
echo "📦 Checking Python dependencies..."
pip install -q fastapi uvicorn python-multipart python-dotenv

# Start the FastAPI server
echo "🌟 Starting LangGraph FastAPI server on http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run with uvicorn
uvicorn app_langgraph:app --host 0.0.0.0 --port 8000 --reload --log-level info