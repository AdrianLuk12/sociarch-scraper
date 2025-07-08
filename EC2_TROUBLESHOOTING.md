# EC2 Troubleshooting Guide

## Issue: Browser Hangs at "enabling autodiscover targets"

### Symptoms
```
2025-07-08 23:06:37,614 - zendriver.core.browser - INFO - enabling autodiscover targets
(hangs indefinitely)
```

### Root Causes
1. **Missing Chrome dependencies** - Most common cause
2. **Insufficient Chrome flags** for headless operation
3. **Memory/resource constraints**
4. **X11/display issues** even in headless mode
5. **Network/firewall restrictions**

### Quick Fix

**Step 1: Run the automated setup script**
```bash
# Download and run the comprehensive setup script
curl -O https://raw.githubusercontent.com/your-repo/sociarch-scraper/main/setup_ec2.sh
chmod +x setup_ec2.sh
sudo ./setup_ec2.sh
```

**Step 2: Validate the setup**
```bash
cd /home/ubuntu/sociarch-scraper  # or /home/ec2-user/sociarch-scraper
./validate_ec2.sh
```

**Step 3: Test the scraper**
```bash
./start_scraper.sh
```

### Manual Troubleshooting

#### 1. Check Chrome Installation
```bash
# Test basic Chrome functionality
google-chrome --version
google-chrome --headless --no-sandbox --disable-gpu --dump-dom about:blank
```

#### 2. Install Missing Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y libnss3 libgconf-2-4 libxss1 libappindicator1 \
    libindicator7 fonts-liberation libgbm1 libxrandr2 libasound2 \
    libpangocairo-1.0-0 libatk1.0-0 libcairo-gobject2 libgtk-3-0 \
    libgdk-pixbuf2.0-0 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrender1 libxtst6 ca-certificates \
    libxext6 libxi6 xvfb

# Amazon Linux/CentOS/RHEL
sudo yum install -y nss atk at-spi2-atk cups-libs gtk3 \
    libXcomposite libXcursor libXdamage libXext libXi libXrandr \
    libXScrnSaver libXtst pango alsa-lib xorg-x11-server-Xvfb
```

#### 3. Test Chrome with Exact Scraper Settings
```bash
timeout 30 google-chrome \
    --headless \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --single-process \
    --disable-extensions \
    --disable-plugins \
    --disable-images \
    --remote-debugging-port=9222 \
    --dump-dom about:blank
```

If this command hangs or fails, Chrome dependencies are incomplete.

#### 4. Check Memory and Resources
```bash
# Check available memory
free -h

# Check disk space
df -h

# Check CPU usage
top
```

**Minimum requirements:**
- 1GB RAM (2GB recommended)
- 1GB free disk space
- t2.micro or larger instance

#### 5. Environment Variables
Ensure these are set in your `.env` file:
```bash
ENV=production
NO_SANDBOX=true
HEADLESS_MODE=true
SCRAPER_TIMEOUT=120
SINGLE_PROCESS=true
```

### Instance Type Recommendations

| Instance Type | Memory | Status | Notes |
|---------------|--------|--------|-------|
| t2.nano      | 0.5GB  | ❌ Not Recommended | Insufficient memory |
| t2.micro     | 1GB    | ✅ Minimum | Free tier, basic functionality |
| t2.small     | 2GB    | ✅ Recommended | Better performance |
| t2.medium+   | 4GB+   | ✅ Optimal | Best performance |

### Common Error Messages and Solutions

#### "Chrome not reachable"
```bash
# Install Chrome properly
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
sudo apt update
sudo apt install -y google-chrome-stable
```

#### "Browser initialization timed out"
- Increase timeout in environment: `SCRAPER_TIMEOUT=180`
- Use larger instance type
- Check available memory

#### "Failed to connect to DevTools"
- Add `--remote-debugging-port=0` flag
- Check firewall settings
- Ensure single-process mode: `--single-process`

#### "Session not created"
- Clear Chrome user data: `rm -rf /tmp/.com.google.Chrome*`
- Restart with fresh user data dir

### Advanced Debugging

#### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python main.py
```

#### Check Chrome Process
```bash
# Check if Chrome processes are running
ps aux | grep chrome

# Kill stuck Chrome processes
pkill -f chrome
```

#### Test Network Connectivity
```bash
# Test if the scraper can reach the target site
curl -I https://hkmovie6.com/

# Note: EC2 detection now uses username instead of metadata service
# to avoid 401 unauthorized errors with metadata service
```

#### Memory Management
```bash
# Add swap space if memory is limited
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Prevention

1. **Use the setup script** for new instances
2. **Validate before running** with `./validate_ec2.sh`
3. **Monitor resources** during execution
4. **Use appropriate instance sizes**
5. **Keep Chrome updated** regularly

### Getting Help

If you're still experiencing issues:

1. **Run the validation script**: `./validate_ec2.sh`
2. **Check the logs**: `tail -f movie_scraper.log`
3. **Test Chrome manually** with the commands above
4. **Verify your instance size** and available resources

### Emergency Recovery

If the scraper is completely stuck:

```bash
# Kill all Chrome processes
sudo pkill -f chrome

# Clear temporary files
sudo rm -rf /tmp/.com.google.Chrome*
sudo rm -rf /tmp/core.zendriver*

# Restart the scraper
./start_scraper.sh
``` 