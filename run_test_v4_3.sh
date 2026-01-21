#!/bin/bash
# Test script for Faculty Pipeline v4.3

set -e

cd "$(dirname "$0")"

# Set environment variables
export OPENALEX_CONTACT_EMAIL="riqlabmatch@gmail.com"
export BRAVE_API_KEY="BSAcKzgthbeCluu_MuOibiYz0VQRqLO"

# Install dependencies if needed
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install requests beautifulsoup4
fi

# Run test with 20 faculty
echo "Starting Faculty Pipeline v4.3 Test (20 faculty)..."
echo "API Key: ${BRAVE_API_KEY:0:10}..."
echo ""

# Use caffeinate on Mac to prevent sleep
if command -v caffeinate &> /dev/null; then
    echo "Using caffeinate to keep system awake..."
    caffeinate -i python3 faculty_pipeline_v4_3.py \
        --institution harvard \
        --max-faculty 20 \
        --verbose \
        --log-file test_v4_3_20faculty.log \
        --output output
else
    python3 faculty_pipeline_v4_3.py \
        --institution harvard \
        --max-faculty 20 \
        --verbose \
        --log-file test_v4_3_20faculty.log \
        --output output
fi

echo ""
echo "Test complete! Check output/ directory for results."
echo "Checkpoints saved in checkpoints/ directory."
