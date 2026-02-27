#!/bin/bash
# Pipeline launcher that keeps running even after computer restart
# This script will restart the pipeline automatically

cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and fill in your API keys"
    exit 1
fi

LOG_FILE="harvard_600_v43.log"
STDOUT_LOG="harvard_600_v43_stdout.log"
PID_FILE="/tmp/faculty_pipeline_600.pid"

# Function to check if pipeline is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start pipeline
start_pipeline() {
    echo "$(date): Starting pipeline..."
    
    # Use nohup and caffeinate to keep running
    nohup caffeinate -i python3 faculty_pipeline_v4_3.py \
        --institution harvard \
        --max-faculty 600 \
        --output output \
        --log-file "$LOG_FILE" > "$STDOUT_LOG" 2>&1 &
    
    echo $! > "$PID_FILE"
    echo "$(date): Pipeline started with PID: $(cat $PID_FILE)"
}

# Check if already running
if is_running; then
    echo "$(date): Pipeline already running (PID: $(cat $PID_FILE))"
    exit 0
fi

# Check if completed
if grep -q "PIPELINE COMPLETE" "$LOG_FILE" 2>/dev/null || grep -q "PIPELINE COMPLETE" "$STDOUT_LOG" 2>/dev/null; then
    echo "$(date): Pipeline already completed!"
    exit 0
fi

# Start pipeline
start_pipeline

echo ""
echo "✅ Pipeline started!"
echo "📊 Monitor with: tail -f $LOG_FILE"
echo "🔄 Check status with: bash check_status.sh"
echo ""
echo "⚠️  IMPORTANT: Keep your computer powered on!"
echo "   - Caffeinate prevents sleep, but NOT manual shutdown"
echo "   - Don't shut down or restart your computer during the run"
echo "   - Estimated time: 5-7 hours"
