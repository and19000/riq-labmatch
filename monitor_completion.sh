#!/bin/bash
# Monitor pipeline completion and notify when finished

LOG_FILE="harvard_v44_resume.log"
CHECK_INTERVAL=60  # Check every 60 seconds

echo "Monitoring pipeline for completion..."
echo "Log file: $LOG_FILE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    # Check if pipeline process is running
    if ! ps aux | grep -q "[f]aculty_pipeline_v4_4.py"; then
        # Check if it completed successfully
        if grep -qi "PIPELINE COMPLETE\|FINAL STATISTICS\|Pipeline complete" "$LOG_FILE" 2>/dev/null; then
            echo ""
            echo "=========================================="
            echo "✅ PIPELINE COMPLETED SUCCESSFULLY!"
            echo "=========================================="
            echo ""
            
            # Show final stats
            echo "Final Statistics:"
            tail -20 "$LOG_FILE" | grep -A 10 "FINAL STATISTICS" || tail -15 "$LOG_FILE"
            
            echo ""
            echo "Output files:"
            ls -lt output/harvard_university_*.json 2>/dev/null | head -2 || echo "  (Check output directory)"
            ls -lt output/harvard_university_*.csv 2>/dev/null | head -2 || echo "  (Check output directory)"
            
            # Make a sound notification (works on macOS)
            if command -v afplay >/dev/null 2>&1; then
                afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
            fi
            
            # Display notification (works on macOS)
            if command -v osascript >/dev/null 2>&1; then
                osascript -e 'display notification "Pipeline completed successfully!" with title "Faculty Pipeline v4.4"' 2>/dev/null || true
            fi
            
            break
        else
            echo ""
            echo "⚠️ Pipeline process stopped but completion not detected"
            echo "Check the log file for errors: $LOG_FILE"
            tail -20 "$LOG_FILE"
            break
        fi
    fi
    
    # Show progress
    if [ -f "$LOG_FILE" ]; then
        # Extract latest phase and progress
        LATEST=$(tail -5 "$LOG_FILE" | grep -E "PHASE|Progress|\[.*\/.*\]" | tail -1)
        if [ -n "$LATEST" ]; then
            echo -ne "\r$(date '+%H:%M:%S') - Status: $LATEST"
        fi
    fi
    
    sleep $CHECK_INTERVAL
done

echo ""
echo "Monitoring stopped."
