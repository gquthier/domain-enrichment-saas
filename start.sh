#!/bin/bash

# Domain Enrichment SaaS - Quick Start Script

echo "🚀 Starting Domain Enrichment SaaS..."
echo ""

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✓ Docker detected"
    echo "Starting with Docker Compose..."
    docker-compose up -d
    echo ""
    echo "✅ Application started!"
    echo "📱 Open your browser: http://localhost:8000"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop: docker-compose down"
else
    echo "⚠️  Docker not found. Starting with Python..."
    echo ""

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt

    # Start the application
    echo ""
    echo "✅ Starting application..."
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

    echo ""
    echo "📱 Open your browser: http://localhost:8000"
    echo "🛑 Stop: Press Ctrl+C"
fi
