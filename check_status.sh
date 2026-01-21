#!/bin/bash
# Quick status check for pipeline

LOG_FILE="harvard_600_v43.log"
STDOUT_LOG="harvard_600_v43_stdout.log"

echo "=== Pipeline Status Check ==="
echo "Time: $(date)"
echo ""

# Check if process is running
PID=$(ps aux | grep "faculty_pipeline_v4_3.py.*max-faculty 600" | grep -v grep | awk '{print $2}' | head -1)
if [ -z "$PID" ]; then
    echo "❌ Pipeline NOT running"
    
    # Check if completed
    if grep -q "PIPELINE COMPLETE" $LOG_FILE 2>/dev/null || grep -q "PIPELINE COMPLETE" $STDOUT_LOG 2>/dev/null; then
        echo "✅ Pipeline completed successfully!"
        echo ""
        echo "Last lines:"
        tail -10 $LOG_FILE 2>/dev/null || tail -10 $STDOUT_LOG 2>/dev/null
    else
        echo "⚠️ Pipeline stopped unexpectedly"
        echo ""
        echo "Last 10 lines:"
        tail -10 $LOG_FILE 2>/dev/null || tail -10 $STDOUT_LOG 2>/dev/null
    fi
else
    echo "✅ Pipeline running (PID: $PID)"
    echo ""
    
    # Show progress from logs
    echo "=== Recent Progress ==="
    if [ -f "$LOG_FILE" ]; then
        # Extract key stats
        grep -E "(Page |Directory|Faculty needing search|Found:|Progress:|Checkpoint saved)" $LOG_FILE | tail -15
    else
        tail -15 $STDOUT_LOG 2>/dev/null | head -15
    fi
    
    echo ""
    echo "=== Last Activity ==="
    tail -5 $LOG_FILE 2>/dev/null || tail -5 $STDOUT_LOG 2>/dev/null
fi

echo ""
echo "=== Checkpoint Status ==="
if [ -d "checkpoints" ]; then
    LATEST_CHECKPOINT=$(ls -t checkpoints/*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_CHECKPOINT" ]; then
        echo "Latest checkpoint: $LATEST_CHECKPOINT"
        echo "Modified: $(stat -f "%Sm" "$LATEST_CHECKPOINT" 2>/dev/null || stat -c "%y" "$LATEST_CHECKPOINT" 2>/dev/null)"
    else
        echo "No checkpoints found"
    fi
else
    echo "No checkpoints directory"
fi

echo ""
echo "=== Resource Usage ==="
if [ -n "$PID" ]; then
    ps -p $PID -o pid,%cpu,%mem,etime,command | tail -1
fi
