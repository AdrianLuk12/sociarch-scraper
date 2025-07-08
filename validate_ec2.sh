#!/bin/bash

# EC2 Movie Scraper Validation Script
echo "Validating EC2 Movie Scraper Deployment"
echo "========================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running on EC2
if [[ "$USER" == "ec2-user" || "$USER" == "ubuntu" ]]; then
    echo "[OK] Running on EC2 (detected user: $USER)"
    IS_EC2=true
    # Try to get instance ID if metadata service is available
    INSTANCE_ID=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
    if [ "$INSTANCE_ID" != "unknown" ]; then
        echo "[INFO] Instance ID: $INSTANCE_ID"
    fi
else
    echo "[WARN] Not running on EC2 (user: $USER) - this is OK for local testing"
    IS_EC2=false
fi

# Check Python installation
if command_exists python3; then
    echo "[OK] Python 3 found: $(python3 --version)"
else
    echo "[FAIL] Python 3 not found. Please install Python 3."
    exit 1
fi

# Check Chrome installation with detailed validation
if command_exists google-chrome; then
    CHROME_VERSION=$(google-chrome --version 2>/dev/null || echo "Unknown")
    echo "[OK] Chrome found: $CHROME_VERSION"
    
    # Test Chrome dependencies on EC2
    if [ "$IS_EC2" = "true" ]; then
        echo "[INFO] Testing Chrome dependencies on EC2..."
        
        # Test basic Chrome startup
        if google-chrome --headless --no-sandbox --disable-gpu --dump-dom about:blank >/dev/null 2>&1; then
            echo "[OK] Chrome basic test passed"
        else
            echo "[FAIL] Chrome basic test failed - missing dependencies"
            echo "[INFO] Installing missing Chrome dependencies..."
            sudo apt update -y >/dev/null 2>&1
            sudo apt install -y \
                libnss3 \
                libgconf-2-4 \
                libxss1 \
                libappindicator1 \
                libindicator7 \
                fonts-liberation \
                libgbm1 \
                libxrandr2 \
                libasound2 \
                libpangocairo-1.0-0 \
                libatk1.0-0 \
                libcairo-gobject2 \
                libgtk-3-0 \
                libgdk-pixbuf2.0-0 >/dev/null 2>&1
            
            # Test again
            if google-chrome --headless --no-sandbox --disable-gpu --dump-dom about:blank >/dev/null 2>&1; then
                echo "[OK] Chrome dependencies installed successfully"
            else
                echo "[FAIL] Chrome still failing after dependency installation"
                exit 1
            fi
        fi
    fi
else
    echo "[FAIL] Chrome not found."
    if [ "$IS_EC2" = "true" ]; then
        echo "[INFO] Installing Google Chrome on EC2..."
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add - 2>/dev/null
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
        sudo apt update -y >/dev/null 2>&1
        sudo apt install -y google-chrome-stable >/dev/null 2>&1
        
        if command_exists google-chrome; then
            echo "[OK] Chrome installed successfully: $(google-chrome --version)"
        else
            echo "[FAIL] Failed to install Chrome"
            exit 1
        fi
    else
        echo "[INFO] Please install Google Chrome manually"
        exit 1
    fi
fi

# Check for X11 dependencies (useful for debugging)
if [ "$IS_EC2" = "true" ]; then
    if command_exists Xvfb; then
        echo "[OK] Xvfb (virtual display) available"
    else
        echo "[WARN] Xvfb not found, installing..."
        sudo apt install -y xvfb >/dev/null 2>&1
        if command_exists Xvfb; then
            echo "[OK] Xvfb installed successfully"
        else
            echo "[WARN] Failed to install Xvfb (not critical for headless mode)"
        fi
    fi
fi

# Check virtual environment
if [ -d "venv" ]; then
    echo "[OK] Virtual environment found"
    
    # Check if packages are installed
    if venv/bin/pip list | grep -q "zendriver"; then
        echo "[OK] Required Python packages installed"
        
        # Test zendriver import
        if venv/bin/python -c "import zendriver" 2>/dev/null; then
            echo "[OK] Zendriver imports successfully"
        else
            echo "[FAIL] Zendriver import failed"
            exit 1
        fi
    else
        echo "[FAIL] Missing Python packages. Run: pip install -r requirements.txt"
        exit 1
    fi
else
    echo "[FAIL] Virtual environment not found. Please run setup first."
    exit 1
fi

# Check environment file
if [ -f ".env" ]; then
    echo "[OK] .env file found"
    
    if grep -q "SUPABASE_URL=" .env && ! grep -q "SUPABASE_URL=your_supabase_url" .env; then
        echo "[OK] SUPABASE_URL configured"
    else
        echo "[WARN] Please configure SUPABASE_URL in .env file"
    fi
    
    if grep -q "SUPABASE_KEY=" .env && ! grep -q "SUPABASE_KEY=your_supabase_key" .env; then
        echo "[OK] SUPABASE_KEY configured"
    else
        echo "[WARN] Please configure SUPABASE_KEY in .env file"
    fi
else
    echo "[FAIL] .env file not found. Copy from env.template"
    exit 1
fi

# Check script permissions
if [ -x "start_scraper.sh" ]; then
    echo "[OK] start_scraper.sh is executable"
else
    echo "[WARN] start_scraper.sh not executable. Running: chmod +x start_scraper.sh"
    chmod +x start_scraper.sh
fi

if [ -x "daily_scraper.sh" ]; then
    echo "[OK] daily_scraper.sh is executable"
else
    echo "[WARN] daily_scraper.sh not executable. Running: chmod +x daily_scraper.sh"
    chmod +x daily_scraper.sh
fi

# Test network connectivity
if curl -s --connect-timeout 10 https://hkmovie6.com > /dev/null; then
    echo "[OK] Can reach hkmovie6.com"
else
    echo "[FAIL] Cannot reach hkmovie6.com. Check network connectivity."
    exit 1
fi

# Check system resources
MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEMORY_MB=$((MEMORY_KB / 1024))

if [ $MEMORY_MB -gt 1000 ]; then
    echo "[OK] Sufficient memory: ${MEMORY_MB}MB"
else
    echo "[WARN] Low memory: ${MEMORY_MB}MB. Consider adding swap or using larger instance."
fi

# Check disk space
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "[OK] Sufficient disk space (${DISK_USAGE}% used)"
else
    echo "[WARN] High disk usage: ${DISK_USAGE}%. Consider cleaning up or expanding storage."
fi

# Final Chrome test with exact scraper settings
echo "[INFO] Testing Chrome with scraper settings..."
if [ "$IS_EC2" = "true" ]; then
    if timeout 30 google-chrome \
        --headless \
        --no-sandbox \
        --disable-gpu \
        --disable-dev-shm-usage \
        --single-process \
        --disable-extensions \
        --disable-plugins \
        --disable-images \
        --remote-debugging-port=9222 \
        --dump-dom about:blank > /dev/null 2>&1; then
        echo "[OK] Chrome test with scraper settings passed"
    else
        echo "[FAIL] Chrome test with scraper settings failed"
        echo "[INFO] This indicates the browser will hang during 'enabling autodiscover targets'"
        exit 1
    fi
fi

echo ""
echo "EC2 validation complete!"
echo "Ready to run: ./start_scraper.sh" 