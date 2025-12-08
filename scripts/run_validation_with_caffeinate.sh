#!/bin/bash
# Script to run website validation and prevent computer from sleeping

cd "$(dirname "$0")/.."

echo "Starting website validation..."
echo "This will process all 1231 faculty members and may take several hours."
echo "Your computer will stay awake while the script runs."
echo ""
echo "To monitor progress, run: bash scripts/check_progress.sh"
echo "Or watch the log: tail -f /tmp/website_validation_full.log"
echo ""
echo "To stop the script and allow sleep again:"
echo "  pkill -f validate_websites.py"
echo "  pkill caffeinate"
echo ""

# Activate virtual environment and run with caffeinate
source venv/bin/activate

# Start the validation script
nohup python scripts/validate_websites.py 0 1231 > /tmp/website_validation_full.log 2>&1 &
SCRIPT_PID=$!

# Keep computer awake while script runs
caffeinate -w $SCRIPT_PID &
CAFFEINATE_PID=$!

echo "Script started (PID: $SCRIPT_PID)"
echo "Caffeinate running (PID: $CAFFEINATE_PID)"
echo ""
echo "Script is running in background. Your computer will stay awake."
echo "Check progress with: bash scripts/check_progress.sh"


