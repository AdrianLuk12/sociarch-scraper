#!/usr/bin/env python3
"""
EC2 Deployment Setup Script for Movie Scraper
Run this script after setting up your EC2 instance to prepare the environment.
"""
import os
import subprocess
import sys
import stat
from pathlib import Path

def run_command(cmd, description=""):
    """Run a system command and handle errors"""
    print(f"🔄 {description or cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   Stderr: {e.stderr.strip()}")
        return False

def create_startup_script():
    """Create a startup script for the scraper"""
    startup_script = """#!/bin/bash
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
"""
    
    script_path = Path("start_scraper.sh")
    with open(script_path, 'w') as f:
        f.write(startup_script)
    
    # Make script executable
    os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    print(f"✅ Created startup script: {script_path}")

def create_systemd_service():
    """Create systemd service file for automatic startup"""
    service_content = """[Unit]
Description=Movie Scraper Service
After=network.target

[Service]
Type=oneshot
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/sociarch-scraper
ExecStart=/home/ec2-user/sociarch-scraper/start_scraper.sh
Environment=HOME=/home/ec2-user
Environment=USER=ec2-user
StandardOutput=journal
StandardError=journal
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path("movie-scraper.service")
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print(f"✅ Created systemd service file: {service_path}")
    print("   To install: sudo cp movie-scraper.service /etc/systemd/system/")
    print("   To enable: sudo systemctl enable movie-scraper.service")

def create_cron_script():
    """Create cron script for scheduled execution"""
    cron_script = """#!/bin/bash
# Daily Movie Scraper Cron Job Script
# Add to crontab with: 0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/ec2-user"

# Log start time
echo "$(date): Starting daily movie scraper" >> /home/ec2-user/scraper.log

# Navigate to project directory
cd /home/ec2-user/sociarch-scraper

# Run the scraper
./start_scraper.sh >> /home/ec2-user/scraper.log 2>&1

# Log completion
echo "$(date): Daily movie scraper completed" >> /home/ec2-user/scraper.log

# Optional: Stop instance after completion
# aws ec2 stop-instances --instance-ids $(curl -s http://169.254.169.254/latest/meta-data/instance-id) --region $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed 's/[a-z]$//')
"""
    
    script_path = Path("daily_scraper.sh")
    with open(script_path, 'w') as f:
        f.write(cron_script)
    
    # Make script executable
    os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    print(f"✅ Created cron script: {script_path}")

def install_dependencies():
    """Install system dependencies for EC2"""
    print("🔄 Installing system dependencies...")
    
    # Update system
    run_command("sudo yum update -y", "Updating system packages")
    
    # Install Python 3 and pip
    run_command("sudo yum install -y python3 python3-pip", "Installing Python 3")
    
    # Install Chrome dependencies
    chrome_deps = [
        "wget", "unzip", "curl", "xvfb", 
        "libX11", "libXcomposite", "libXcursor", "libXdamage", "libXext",
        "libXi", "libXrandr", "libXrender", "libXss", "libXtst",
        "ca-certificates", "fonts-liberation", "libappindicator1",
        "libnss3", "lsb-release", "xdg-utils", "libxss1", "libgconf-2-4",
        "libdrm2", "libxkbcommon0", "libgtk-3-0"
    ]
    
    for dep in chrome_deps:
        run_command(f"sudo yum install -y {dep}", f"Installing {dep}")
    
    # Install Chrome
    print("🔄 Installing Google Chrome...")
    run_command("wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -")
    run_command("sudo sh -c 'echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" >> /etc/apt/sources.list.d/google.list'")
    run_command("sudo yum update -y")
    run_command("sudo yum install -y google-chrome-stable")

def setup_environment():
    """Set up the Python environment"""
    print("🔄 Setting up Python environment...")
    
    # Create virtual environment
    if not Path("venv").exists():
        run_command("python3 -m venv venv", "Creating virtual environment")
    
    # Activate and install requirements
    run_command("source venv/bin/activate && pip install --upgrade pip", "Upgrading pip")
    run_command("source venv/bin/activate && pip install -r requirements.txt", "Installing Python dependencies")

def create_env_template():
    """Create .env template file"""
    env_template = """# Environment Variables for Movie Scraper
# Copy this file to .env and fill in your values

# Required - Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Optional - Supabase Configuration
SUPABASE_SCHEMA=knowledge_base
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# EC2 Optimized Settings
HEADLESS_MODE=true
NO_SANDBOX=true
SCRAPER_TIMEOUT=180
SCRAPER_DELAY=0.5

# Optional - Override if needed
# HEADLESS_MODE=false  # Set to false for debugging
# SCRAPER_TIMEOUT=300  # Increase if pages load slowly
"""
    
    env_path = Path("env.template")
    with open(env_path, 'w') as f:
        f.write(env_template)
    
    print(f"✅ Created environment template: {env_path}")
    print("   Copy to .env and configure your Supabase settings")

def main():
    """Main deployment setup function"""
    print("🚀 Setting up Movie Scraper for EC2 Deployment")
    print("=" * 50)
    
    # Check if running on EC2
    try:
        response = subprocess.run(
            ["curl", "-s", "--max-time", "5", "http://169.254.169.254/latest/meta-data/instance-id"],
            capture_output=True, text=True
        )
        if response.returncode == 0 and response.stdout:
            print(f"✅ Detected EC2 Instance ID: {response.stdout.strip()}")
        else:
            print("⚠️  Not running on EC2 - some features may not work")
    except:
        print("⚠️  Could not detect EC2 environment")
    
    # Create deployment scripts
    print("\n📝 Creating deployment scripts...")
    create_startup_script()
    create_systemd_service()
    create_cron_script()
    create_env_template()
    
    # Install dependencies (commented out - requires manual installation)
    # print("\n📦 Installing dependencies...")
    # install_dependencies()
    
    # Setup Python environment
    print("\n🐍 Setting up Python environment...")
    setup_environment()
    
    print("\n✅ EC2 deployment setup complete!")
    print("\n📋 Next steps:")
    print("1. Copy env.template to .env and configure your Supabase settings")
    print("2. Test the scraper: ./start_scraper.sh")
    print("3. For automatic startup: sudo cp movie-scraper.service /etc/systemd/system/")
    print("4. For daily scheduling: crontab -e and add: 0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh")
    print("\n🔗 See README.md for detailed EC2 hosting instructions")

if __name__ == "__main__":
    main() 