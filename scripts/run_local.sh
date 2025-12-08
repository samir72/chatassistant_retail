#!/bin/bash
# Run chatbot locally with full features

echo "=========================================="
echo "🛒 Retail Inventory Assistant - Local Mode"
echo "=========================================="
echo ""

# Set deployment mode
export DEPLOYMENT_MODE=local

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if package is installed
if ! python -c "import chatassistant_retail" 2>/dev/null; then
    echo "📦 Installing package..."
    pip install -e .
fi

echo "✅ Environment ready"
echo ""
echo "Starting Gradio interface..."
echo "Access at: http://127.0.0.1:7860"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Run the application
python -m chatassistant_retail
