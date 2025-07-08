#!/bin/bash

# EC2 Movie Scraper Validation Script
echo "Validating EC2 Movie Scraper Deployment"
echo "========================================"

# Check if running on EC2
INSTANCE_ID=$(curl -s --connect-timeout 5 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$INSTANCE_ID" ]; then
    echo "[OK] Running on EC2 instance: $INSTANCE_ID"
else
    echo "[WARN] Not running on EC2 (this is OK for local testing)"
fi

# Check Python installation
if command -v python3 &> /dev/null; then
    echo "[OK] Python 3 found: $(python3 --version)"
else
    echo "[FAIL] Python 3 not found. Please install Python 3."
    exit 1
fi

# Check Chrome installation
if command -v google-chrome &> /dev/null; then
    echo "[OK] Chrome found: $(google-chrome --version)"
else
    echo "[FAIL] Chrome not found. Please install Google Chrome."
    exit 1
fi

# Test Chrome in headless mode
if google-chrome --headless --dump-dom https://www.google.com > /dev/null 2>&1; then
    echo "[OK] Chrome headless mode working"
else
    echo "[FAIL] Chrome headless mode failed"
    exit 1
fi

# Check virtual environment
if [ -d "venv" ]; then
    echo "[OK] Virtual environment found"
    
    # Check if packages are installed
    if venv/bin/pip list | grep -q "zendriver"; then
        echo "[OK] Required Python packages installed"
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

echo ""
echo "EC2 validation complete!"
echo "Ready to run: ./start_scraper.sh" 