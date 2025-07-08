#!/bin/bash
# EC2 Deployment Validation Script
# Run this script on EC2 to validate the deployment setup

echo "🔍 Validating EC2 Movie Scraper Deployment"
echo "=" * 50

# Check if running on EC2
echo "🔄 Checking EC2 environment..."
if curl -s --max-time 5 http://169.254.169.254/latest/meta-data/instance-id > /dev/null; then
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    echo "✅ Running on EC2 instance: $INSTANCE_ID"
else
    echo "⚠️  Not running on EC2 (this is OK for local testing)"
fi

# Check Python installation
echo "🔄 Checking Python installation..."
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 found: $(python3 --version)"
else
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check Chrome installation
echo "🔄 Checking Chrome installation..."
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome found: $(google-chrome --version)"
else
    echo "❌ Chrome not found. Please install Google Chrome."
    exit 1
fi

# Test Chrome in headless mode
echo "🔄 Testing Chrome headless mode..."
if google-chrome --headless --no-sandbox --dump-dom https://google.com > /dev/null 2>&1; then
    echo "✅ Chrome headless mode working"
else
    echo "❌ Chrome headless mode failed"
    exit 1
fi

# Check virtual environment
echo "🔄 Checking virtual environment..."
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
    
    # Check required packages
    echo "🔄 Checking Python dependencies..."
    if python -c "import zendriver, supabase" 2>/dev/null; then
        echo "✅ Required Python packages installed"
    else
        echo "❌ Missing Python packages. Run: pip install -r requirements.txt"
        exit 1
    fi
else
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Check environment file
echo "🔄 Checking environment configuration..."
if [ -f ".env" ]; then
    echo "✅ .env file found"
    
    # Check for required variables
    if grep -q "SUPABASE_URL=your_supabase_project_url" .env; then
        echo "⚠️  Please configure SUPABASE_URL in .env file"
    else
        echo "✅ SUPABASE_URL configured"
    fi
    
    if grep -q "SUPABASE_KEY=your_supabase_anon_key" .env; then
        echo "⚠️  Please configure SUPABASE_KEY in .env file"
    else
        echo "✅ SUPABASE_KEY configured"
    fi
else
    echo "❌ .env file not found. Copy from env.template"
    exit 1
fi

# Check script permissions
echo "🔄 Checking script permissions..."
if [ -x "start_scraper.sh" ]; then
    echo "✅ start_scraper.sh is executable"
else
    echo "⚠️  start_scraper.sh not executable. Running: chmod +x start_scraper.sh"
    chmod +x start_scraper.sh
fi

if [ -x "daily_scraper.sh" ]; then
    echo "✅ daily_scraper.sh is executable"
else
    echo "⚠️  daily_scraper.sh not executable. Running: chmod +x daily_scraper.sh"
    chmod +x daily_scraper.sh
fi

# Test network connectivity
echo "🔄 Testing network connectivity..."
if curl -s --max-time 10 https://hkmovie6.com > /dev/null; then
    echo "✅ Can reach hkmovie6.com"
else
    echo "❌ Cannot reach hkmovie6.com. Check network connectivity."
    exit 1
fi

# Memory check
echo "🔄 Checking available memory..."
MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEMORY_MB=$((MEMORY_KB / 1024))
if [ $MEMORY_MB -gt 512 ]; then
    echo "✅ Sufficient memory: ${MEMORY_MB}MB"
else
    echo "⚠️  Low memory: ${MEMORY_MB}MB. Consider adding swap or using larger instance."
fi

# Disk space check
echo "🔄 Checking disk space..."
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ Sufficient disk space (${DISK_USAGE}% used)"
else
    echo "⚠️  High disk usage: ${DISK_USAGE}%. Consider cleaning up or expanding storage."
fi

echo ""
echo "🎉 EC2 validation complete!"
echo ""
echo "📋 Ready to run:"
echo "1. Test scraper: ./start_scraper.sh"
echo "2. Setup cron job: crontab -e"
echo "3. Monitor logs: tail -f /home/ec2-user/scraper.log" 