#!/bin/bash
# Script to run website validation

cd "$(dirname "$0")/.."

echo "Starting website validation..."
echo "This will process all 1231 faculty members and may take several hours."
echo "Progress will be saved every 25 entries."
echo ""
echo "To monitor progress, run: bash scripts/check_progress.sh"
echo "Or watch the log: tail -f /tmp/website_validation_full.log"
echo ""

# Activate virtual environment and run
source venv/bin/activate
python scripts/validate_websites.py 0 1231 > /tmp/website_validation_full.log 2>&1

echo ""
echo "Validation complete! Check /tmp/website_validation_full.log for results."


