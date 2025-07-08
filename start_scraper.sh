#!/bin/bash

# Movie Scraper Startup Script for EC2
# Optimized for production deployment with auto-shutdown option

set -e

echo "Starting Movie Scraper on EC2..."
echo "================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check EC2 environment
is_ec2() {
    # Check if username is typical EC2 user (more reliable than metadata service)
    [[ "$USER" == "ec2-user" || "$USER" == "ubuntu" ]]
}

# Detect environment
if is_ec2; then
    echo "[INFO] Running on EC2 instance"
    export IS_EC2=true
else
    echo "[INFO] Running locally"
    export IS_EC2=false
fi

# Check Chrome installation
if ! command_exists google-chrome; then
    echo "[ERROR] Google Chrome not found!"
    if [ "$IS_EC2" = "true" ]; then
        echo "[INFO] Installing Chrome on EC2..."
        # Install Chrome
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add - 2>/dev/null || true
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' 2>/dev/null || true
        sudo apt update -y >/dev/null 2>&1 || true
        sudo apt install -y google-chrome-stable >/dev/null 2>&1 || true
        
        if ! command_exists google-chrome; then
            echo "[ERROR] Failed to install Chrome automatically"
            exit 1
        fi
        echo "[INFO] Chrome installed successfully"
    else
        echo "[ERROR] Please install Google Chrome"
        exit 1
    fi
fi

# Set up environment
export DISPLAY=:99
export ENV=production
export RUN_ONCE=true
export NO_SANDBOX=true
export HEADLESS_MODE=true
export SCRAPER_TIMEOUT=120
export DEFAULT_DELAY=1

# Start virtual display for Chrome (if not running headless and X not available)
if [ "$IS_EC2" = "true" ] && ! pgrep Xvfb > /dev/null 2>&1; then
    echo "[INFO] Starting virtual display for EC2..."
    if command_exists Xvfb; then
        Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
        sleep 2
    else
        echo "[WARN] Xvfb not found, relying on headless mode"
    fi
fi

# Navigate to project directory
if [ -d "/home/ubuntu/sociarch-scraper" ]; then
    cd /home/ubuntu/sociarch-scraper
elif [ -d "/home/ec2-user/sociarch-scraper" ]; then
    cd /home/ec2-user/sociarch-scraper
else
    echo "[ERROR] Project directory not found"
    exit 1
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "[INFO] Virtual environment activated"
else
    echo "[ERROR] Virtual environment not found"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo "[INFO] Environment variables loaded"
else
    echo "[WARN] .env file not found, using defaults"
fi

# Run the scraper with enhanced error handling
echo "[INFO] Starting movie scraper..."
python main.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "[INFO] Movie scraper completed successfully"
else
    echo "[ERROR] Movie scraper failed with exit code $exit_code"
fi

# Optional: Auto-shutdown after completion (remove if not desired)
if [ "${AUTO_SHUTDOWN:-false}" = "true" ] && [ "$IS_EC2" = "true" ]; then
    echo "[INFO] Auto-shutdown enabled, stopping instance in 5 minutes..."
    sudo shutdown -h +5 "Movie scraper completed, auto-shutdown in 5 minutes"
fi

echo "[INFO] Startup script completed"
exit $exit_code 