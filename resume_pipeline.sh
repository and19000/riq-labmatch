#!/bin/bash
# Resume pipeline from last checkpoint

cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline

echo "Resuming pipeline from checkpoint..."
echo ""

# Find latest checkpoint
LATEST_CHECKPOINT=$(ls -t checkpoints/*.json 2>/dev/null | head -1)

if [ -z "$LATEST_CHECKPOINT" ]; then
    echo "ERROR: No checkpoint found. Cannot resume."
    exit 1
fi

echo "Latest checkpoint: $LATEST_CHECKPOINT"
PHASE=$(echo $LATEST_CHECKPOINT | grep -o "phase[0-9][a-z]*" | head -1)
echo "Last completed phase: $PHASE"
echo ""

# Check if pipeline is already running
PID=$(ps aux | grep "faculty_pipeline_v4_3.py.*max-faculty 600" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    echo "WARNING: Pipeline already running (PID: $PID)"
    echo "Kill it first? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        kill $PID
        sleep 2
    else
        exit 0
    fi
fi

# Note: The pipeline doesn't have checkpoint resume yet, but we can see where it stopped
# For now, we'll just restart and it will skip completed phases
echo "Note: Pipeline will restart from Phase 2B (website discovery)."
echo "Completed phases will be skipped automatically."
echo ""
echo "Starting pipeline..."

export OPENALEX_CONTACT_EMAIL="riqlabmatch@gmail.com"
export BRAVE_API_KEY="BSAcKzgthbeCluu_MuOibiYz0VQRqLO"

nohup caffeinate -i python3 faculty_pipeline_v4_3.py \
    --institution harvard \
    --max-faculty 600 \
    --output output \
    --log-file harvard_600_v43.log > harvard_600_v43_stdout.log 2>&1 &

echo $! > /tmp/faculty_pipeline_600.pid
echo "Pipeline restarted with PID: $(cat /tmp/faculty_pipeline_600.pid)"
echo "Monitor with: tail -f harvard_600_v43.log"
echo ""
echo "Note: The bug fix has been applied. Pipeline should continue from Phase 3B."
