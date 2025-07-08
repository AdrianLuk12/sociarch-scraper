#!/usr/bin/env python3
"""
Automated EC2 deployment setup script for movie scraper.
Creates all necessary files and configurations for EC2 deployment.
"""

import os
import subprocess
import sys

def run_command(cmd, description=""):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        if description:
            print(f"[OK] {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Error: {e}")
        return None

def create_startup_script():
    """Create the startup script for EC2."""
    script_content = '''#!/bin/bash

# Movie Scraper Startup Script for EC2
# Optimized for production deployment with auto-shutdown option

set -e

echo "Starting Movie Scraper on EC2..."
echo "================================="

# Set up environment
export DISPLAY=:99
export ENV=production
export RUN_ONCE=true
export NO_SANDBOX=true
export HEADLESS_MODE=true
export SCRAPER_TIMEOUT=120
export DEFAULT_DELAY=1

# Start virtual display for Chrome (if not running headless)
if ! pgrep Xvfb > /dev/null; then
    echo "[INFO] Starting virtual display..."
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
    sleep 2
fi

# Navigate to project directory
cd /home/ubuntu/sociarch-scraper

# Activate virtual environment
source venv/bin/activate

# Load environment variables
set -a
source .env
set +a

# Run the scraper
echo "[INFO] Starting movie scraper..."
python main.py

# Optional: Auto-shutdown after completion (remove if not desired)
if [ "${AUTO_SHUTDOWN:-false}" = "true" ]; then
    echo "[INFO] Auto-shutdown enabled, stopping instance in 5 minutes..."
    sudo shutdown -h +5 "Movie scraper completed, auto-shutdown in 5 minutes"
fi

echo "[INFO] Startup script completed"
'''
    
    script_path = "start_scraper.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print(f"[OK] Created startup script: {script_path}")

def create_systemd_service():
    """Create systemd service file for movie scraper."""
    service_content = '''[Unit]
Description=Movie Scraper Service
After=network.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/sociarch-scraper
ExecStart=/home/ubuntu/sociarch-scraper/start_scraper.sh
Environment=PATH=/home/ubuntu/sociarch-scraper/venv/bin:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
'''
    
    service_path = "movie-scraper.service"
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print(f"[OK] Created systemd service file: {service_path}")
    print("To install: sudo cp movie-scraper.service /etc/systemd/system/")
    print("To enable: sudo systemctl enable movie-scraper")

def create_cron_script():
    """Create cron job script for daily scheduling."""
    script_content = '''#!/bin/bash

# Daily Movie Scraper Cron Job
# Add to crontab with: 0 6 * * * /home/ubuntu/sociarch-scraper/daily_scraper.sh

LOG_FILE="/home/ubuntu/sociarch-scraper/cron.log"
SCRIPT_DIR="/home/ubuntu/sociarch-scraper"

echo "$(date): Starting daily movie scraper..." >> "$LOG_FILE"

cd "$SCRIPT_DIR"

# Run the scraper and log output
./start_scraper.sh >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Daily scraper completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Daily scraper failed" >> "$LOG_FILE"
fi

# Keep only last 100 lines of log
tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
'''
    
    script_path = "daily_scraper.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    print(f"[OK] Created cron script: {script_path}")

def create_health_check():
    """Create health check script."""
    script_content = '''#!/bin/bash

# Health check script for movie scraper
if pgrep -f "python.*main.py" > /dev/null; then
    echo "Movie scraper is running"
    exit 0
else
    echo "Movie scraper is not running"
    exit 1
fi
'''
    
    script_path = "health_check.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)

def create_validation_script():
    """Create validation script."""
    # This would be too long to include here, but it's already created
    pass

def create_env_template():
    """Create comprehensive environment template."""
    env_content = '''# Supabase Configuration (Required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
SUPABASE_SCHEMA=public

# Scraper Configuration
ENV=production
RUN_ONCE=true
SCRAPER_TIMEOUT=120
DEFAULT_DELAY=1
SCRAPER_INTERVAL=21600

# Browser Configuration (EC2 Optimized)
HEADLESS_MODE=true
NO_SANDBOX=true

# Logging
LOG_LEVEL=INFO

# Optional: Auto-shutdown after completion
# AUTO_SHUTDOWN=true
'''
    
    env_path = "env.template"
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"[OK] Created environment template: {env_path}")

def main():
    """Main deployment setup function."""
    print("Setting up Movie Scraper for EC2 Deployment")
    print("===========================================")
    
    # Check if we're on EC2
    try:
        result = run_command("curl -s --connect-timeout 5 http://169.254.169.254/latest/meta-data/instance-id", "")
        if result and result.stdout.strip():
            print(f"[OK] Detected EC2 Instance ID: {result.stdout.strip()}")
        else:
            print("[WARN] Not running on EC2 - some features may not work")
    except:
        print("[WARN] Could not detect EC2 environment")
    
    # Create all deployment files
    create_startup_script()
    create_systemd_service()
    create_cron_script()
    create_health_check()
    create_env_template()
    
    # Make all shell scripts executable
    run_command("chmod +x *.sh", "Made shell scripts executable")
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    print("")
    print("[OK] EC2 deployment setup complete!")
    print("")
    print("Next steps:")
    print("1. Copy .env.template to .env and configure your Supabase credentials")
    print("2. Run validation: ./validate_ec2.sh")
    print("3. Test manually: ./start_scraper.sh")
    print("4. Set up cron job: crontab -e")
    print("   Add: 0 6 * * * /home/ubuntu/sociarch-scraper/daily_scraper.sh")
    print("")
    print("For systemd service:")
    print("  sudo cp movie-scraper.service /etc/systemd/system/")
    print("  sudo systemctl enable movie-scraper")
    print("  sudo systemctl start movie-scraper")

if __name__ == "__main__":
    main() 