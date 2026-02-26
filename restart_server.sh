#!/bin/bash

echo "🔄 Restarting FastAPI Server..."

# Kill existing server processes
echo "⏹️  Stopping existing server..."
pkill -f "python.*app.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
sleep 2

# Check if port 5000 is free
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 5000 still in use, waiting..."
    sleep 3
fi

# Start server
echo "🚀 Starting FastAPI server on port 5000..."
cd /home/toshitha/maps
python3 app.py > server.log 2>&1 &

# Wait for server to start
sleep 3

# Verify server is running
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ | grep -q "200"; then
    echo "✅ Server started successfully!"
    echo ""
    echo "🌐 Access points:"
    echo "   Admin Portal: http://localhost:5000/admin"
    echo "   User Portal:  http://localhost:5000/user"
    echo ""
    echo "📋 View logs: tail -f /home/toshitha/maps/server.log"
else
    echo "❌ Server failed to start. Check logs:"
    echo "   tail -f /home/toshitha/maps/server.log"
fi
