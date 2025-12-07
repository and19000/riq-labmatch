#!/bin/bash

# Script to start the Flask server
# This script can run the server in the background so it stays running

cd /Users/kerrynguyen/Projects/riq-labmatch
source venv/bin/activate

# Check if server is already running
if lsof -ti:5001 > /dev/null 2>&1; then
    echo "=================================="
    echo "Server is already running on port 5001"
    echo "Access it at: http://localhost:5001"
    echo "=================================="
    exit 0
fi

echo "=================================="
echo "Starting RIQ Lab Matcher Server..."
echo "=================================="
echo ""
echo "Server will be available at:"
echo "  http://localhost:5001"
echo "  http://127.0.0.1:5001"
echo ""
echo "Note: Using port 5001 to avoid macOS AirPlay conflicts"
echo ""

# Check if user wants to run in background
if [ "$1" == "--background" ] || [ "$1" == "-b" ]; then
    echo "Starting server in background..."
    echo "Server logs will be saved to server.log"
    echo "To stop the server, run: pkill -f 'python app.py'"
    echo ""
    nohup python app.py > server.log 2>&1 &
    echo "Server started! PID: $!"
    echo "Check server.log for output"
else
    echo "Press CTRL+C to stop the server"
    echo ""
    python app.py
fi
