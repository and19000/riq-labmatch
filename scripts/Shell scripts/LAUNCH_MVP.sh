#!/bin/bash
# Launch RIQ LabMatch MVP locally (5-question matching, 1,500 faculty)
# Run from faculty_pipeline/ or project root.

set -e
cd "$(dirname "$0")"

# Use project venv if present (from riq-labmatch root)
if [ -d "../venv" ]; then
  . ../venv/bin/activate
elif [ -d "venv" ]; then
  . venv/bin/activate
fi

echo "=============================================="
echo "RIQ LabMatch MVP"
echo "=============================================="
echo "  URL: http://localhost:5001"
echo "  Sign up: http://localhost:5001/signup"
echo "  Onboarding: 5 questions → matches"
echo "=============================================="
echo ""

export FLASK_ENV=development
export PORT=5001
python app.py
