#!/bin/bash
# Quick monitoring script for v4.5 pipeline

echo "=== Faculty Pipeline v4.5 Status ==="
echo ""

# Check if process is running
if pgrep -f "faculty_pipeline_v4_5.py" > /dev/null; then
    echo "✅ Pipeline is RUNNING"
    echo ""
    echo "Process details:"
    ps aux | grep "faculty_pipeline_v4_5.py" | grep -v grep
else
    echo "❌ Pipeline is NOT running"
fi

echo ""
echo "=== Recent Log Activity ==="
tail -15 harvard_v45.log 2>/dev/null || echo "Log file not found"

echo ""
echo "=== Checkpoint Files ==="
ls -lth checkpoints/harvard_*.json 2>/dev/null | head -5 || echo "No checkpoints yet"

echo ""
echo "=== Output Files ==="
ls -lth output/harvard_university_*.json 2>/dev/null | head -3 || echo "No output files yet"

echo ""
echo "To view live log: tail -f harvard_v45.log"
