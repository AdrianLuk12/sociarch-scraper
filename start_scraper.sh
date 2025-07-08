#!/bin/bash
# Movie Scraper Startup Script
# This script runs the scraper and handles environment setup

# Set environment variables (you may need to adjust these)
export HOME=/home/ec2-user
export USER=ec2-user
export DISPLAY=:99

# Navigate to scraper directory
cd /home/ec2-user/sociarch-scraper

# Activate virtual environment
source venv/bin/activate

# Set EC2-optimized environment variables
export HEADLESS_MODE=true
export NO_SANDBOX=true
export SCRAPER_TIMEOUT=180
export SCRAPER_DELAY=0.5

# Start virtual display for headless Chrome (if needed)
if ! pgrep Xvfb > /dev/null; then
    echo "Starting Xvfb virtual display..."
    Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
    export DISPLAY=:99
fi

# Run the scraper
echo "Starting movie scraper at $(date)"
python3 main.py

# Log completion
echo "Movie scraper completed at $(date)"

# Optional: Shutdown instance after completion (uncomment if desired)
# echo "Shutting down EC2 instance..."
# sudo shutdown -h now 