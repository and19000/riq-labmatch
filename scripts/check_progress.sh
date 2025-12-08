#!/bin/bash
# Quick script to check validation progress

echo "=== Website Validation Progress ==="
echo ""

# Check if script is running
if ps aux | grep -v grep | grep -q "validate_websites.py"; then
    echo "✓ Script is running"
    echo ""
    
    # Get latest progress
    if [ -f /tmp/website_validation_full.log ]; then
        echo "Latest entries processed:"
        tail -20 /tmp/website_validation_full.log | grep -E "\[.*/.*\]" | tail -5
        echo ""
        
        # Count fixes
        FIXED=$(grep -c "→ Fixed:" /tmp/website_validation_full.log 2>/dev/null || echo "0")
        VALID=$(grep -c "✓ Valid" /tmp/website_validation_full.log 2>/dev/null || echo "0")
        INVALID=$(grep -c "✗ Invalid\|✗ No website" /tmp/website_validation_full.log 2>/dev/null || echo "0")
        
        echo "Summary so far:"
        echo "  Valid websites: $VALID"
        echo "  Fixed: $FIXED"
        echo "  Invalid/No website: $INVALID"
    else
        echo "Log file not found yet"
    fi
else
    echo "✗ Script is not running"
    echo ""
    if [ -f /tmp/website_validation_full.log ]; then
        echo "Final results:"
        tail -20 /tmp/website_validation_full.log
    fi
fi


