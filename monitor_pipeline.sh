#!/bin/bash
# Pipeline Monitor and Recovery Script

PIPELINE_PID_FILE="/tmp/faculty_pipeline_600.pid"
LOG_FILE="harvard_600_v43.log"
STDOUT_LOG="harvard_600_v43_stdout.log"
MAX_RESTARTS=3
RESTART_COUNT=0

check_pipeline() {
    # Check if process is running
    if ps -p $(cat $PIPELINE_PID_FILE 2>/dev/null) > /dev/null 2>&1; then
        return 0  # Running
    else
        return 1  # Stopped
    fi
}

restart_pipeline() {
    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        echo "ERROR: Max restarts ($MAX_RESTARTS) reached. Manual intervention needed."
        exit 1
    fi
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "Attempting restart #$RESTART_COUNT at $(date)"
    
    cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline
    export OPENALEX_CONTACT_EMAIL="riqlabmatch@gmail.com"
    export BRAVE_API_KEY="BSAcKzgthbeCluu_MuOibiYz0VQRqLO"
    
    nohup caffeinate -i python3 faculty_pipeline_v4_3.py \
        --institution harvard \
        --max-faculty 600 \
        --output output \
        --log-file harvard_600_v43.log > harvard_600_v43_stdout.log 2>&1 &
    
    echo $! > $PIPELINE_PID_FILE
    echo "Pipeline restarted with PID: $(cat $PIPELINE_PID_FILE)"
}

# Main monitoring loop
echo "Starting pipeline monitor at $(date)"
echo "Log file: $LOG_FILE"

# Wait a bit for initial startup
sleep 10

# Check if PID file exists and get PID
if [ -f "$PIPELINE_PID_FILE" ]; then
    PIPELINE_PID=$(cat $PIPELINE_PID_FILE)
    echo "Monitoring PID: $PIPELINE_PID"
else
    # Find running pipeline process
    PIPELINE_PID=$(ps aux | grep "faculty_pipeline_v4_3.py.*max-faculty 600" | grep -v grep | awk '{print $2}' | head -1)
    if [ -n "$PIPELINE_PID" ]; then
        echo $PIPELINE_PID > $PIPELINE_PID_FILE
        echo "Found running pipeline with PID: $PIPELINE_PID"
    else
        echo "No pipeline process found. Starting new one..."
        restart_pipeline
    fi
fi

# Monitor loop
while true; do
    if ! check_pipeline; then
        echo "WARNING: Pipeline stopped at $(date)"
        echo "Checking last log entries..."
        tail -20 $LOG_FILE 2>/dev/null || tail -20 $STDOUT_LOG 2>/dev/null
        
        # Check for completion
        if grep -q "PIPELINE COMPLETE" $LOG_FILE 2>/dev/null || grep -q "PIPELINE COMPLETE" $STDOUT_LOG 2>/dev/null; then
            echo "Pipeline completed successfully!"
            rm -f $PIPELINE_PID_FILE
            exit 0
        fi
        
        # Attempt restart
        restart_pipeline
        sleep 30  # Wait before next check
    else
        # Log progress every 5 minutes
        if [ $(date +%s) -gt $((LAST_LOG + 300)) ] 2>/dev/null || [ -z "$LAST_LOG" ]; then
            LAST_LOG=$(date +%s)
            echo "$(date): Pipeline running. Last 3 log lines:"
            tail -3 $LOG_FILE 2>/dev/null | head -3 || echo "No log file yet"
            echo "---"
        fi
    fi
    
    sleep 60  # Check every minute
done
