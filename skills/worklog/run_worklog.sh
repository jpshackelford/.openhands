#!/bin/bash
# Quick runner: Generate and serve worklog in one command

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📋 Daily Worklog Runner"
echo "======================="
echo ""

# Generate worklog
echo "🔄 Step 1: Generating worklog..."
python3 "$SCRIPT_DIR/generate_worklog.py"

if [ $? -ne 0 ]; then
    echo "❌ Failed to generate worklog"
    exit 1
fi

echo ""
echo "🌐 Step 2: Starting server..."
echo ""

# Kill any existing server on port 12000
pkill -f "serve_worklog.py" 2>/dev/null

# Start server in background
python3 "$SCRIPT_DIR/serve_worklog.py" > /tmp/worklog_server.log 2>&1 &
SERVER_PID=$!

sleep 2

# Check if server started
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Worklog server started (PID: $SERVER_PID)"
    echo ""
    echo "🔗 View your worklog:"
    echo "   https://work-1-tahhvksgnhffxrqu.prod-runtime.all-hands.dev/"
    echo ""
    echo "🛑 To stop: kill $SERVER_PID"
else
    echo "❌ Failed to start server"
    exit 1
fi
