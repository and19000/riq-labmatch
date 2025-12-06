#!/bin/bash

# Script to start the Flask server

cd /Users/kerrynguyen/Projects/riq-labmatch
source venv/bin/activate

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
echo "Press CTRL+C to stop the server"
echo ""

python app.py





