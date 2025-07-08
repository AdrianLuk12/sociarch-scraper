#!/bin/bash
# Health check script for movie scraper
# Returns 0 if scraper is running, 1 if not

if pgrep -f "python.*main.py" > /dev/null; then
    echo "Scraper is running"
    exit 0
else
    echo "Scraper is not running"
    exit 1
fi 