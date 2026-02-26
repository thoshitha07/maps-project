#!/bin/bash

echo "🚀 Starting FastAPI Server (Clean Start)"
echo "=========================================="

cd /home/toshitha/maps

# Find and display any existing server processes
echo ""
echo "🔍 Checking for existing server processes..."
EXISTING_PID=$(pgrep -f "python.*app.py")

if [ ! -z "$EXISTING_PID" ]; then
    echo "⚠️  Found existing server process: PID $EXISTING_PID"
    echo ""
    echo "To kill it, run one of these commands:"
    echo "  kill $EXISTING_PID"
    echo "  OR press Ctrl+C in the terminal where the server is running"
    echo ""
    echo "After killing, run this script again."
    exit 1
fi

echo "✅ No existing processes found"

# Start fresh server
echo ""
echo "🚀 Starting FastAPI server..."
python3 app.py

