#!/bin/bash

# Comprehensive EC2 Setup Script for Movie Scraper
# This script installs all necessary dependencies to prevent browser hanging issues

set -e

echo "Setting up Movie Scraper for AWS EC2"
echo "===================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if we're on EC2
is_ec2() {
    # Check if username is typical EC2 user (more reliable than metadata service)
    [[ "$USER" == "ec2-user" || "$USER" == "ubuntu" ]]
}

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "[ERROR] Cannot detect OS version"
    exit 1
fi

echo "[INFO] Detected OS: $OS $VER"

# Check if running on EC2
if is_ec2; then
    echo "[INFO] Running on EC2 (detected user: $USER)"
    # Try to get instance ID if metadata service is available
    INSTANCE_ID=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
    if [ "$INSTANCE_ID" != "unknown" ]; then
        echo "[INFO] Instance ID: $INSTANCE_ID"
    fi
else
    echo "[WARN] Not running on EC2 (user: $USER) - continuing anyway"
fi

# Update system packages
echo "[INFO] Updating system packages..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt update -y >/dev/null 2>&1
elif [[ "$OS" == *"Amazon Linux"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum update -y >/dev/null 2>&1 || sudo dnf update -y >/dev/null 2>&1
fi

# Install Python 3 and pip
echo "[INFO] Installing Python 3..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt install -y python3 python3-pip python3-venv >/dev/null 2>&1
elif [[ "$OS" == *"Amazon Linux"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum install -y python3 python3-pip >/dev/null 2>&1 || sudo dnf install -y python3 python3-pip >/dev/null 2>&1
fi

# Install Google Chrome
echo "[INFO] Installing Google Chrome..."
if ! command_exists google-chrome; then
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        # Add Google Chrome repository
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add - 2>/dev/null
        sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
        sudo apt update -y >/dev/null 2>&1
        sudo apt install -y google-chrome-stable >/dev/null 2>&1
    elif [[ "$OS" == *"Amazon Linux"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        # For RHEL-based systems
        sudo yum install -y wget >/dev/null 2>&1
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
        sudo yum localinstall -y google-chrome-stable_current_x86_64.rpm >/dev/null 2>&1
        rm -f google-chrome-stable_current_x86_64.rpm
    fi
    
    if command_exists google-chrome; then
        echo "[OK] Chrome installed: $(google-chrome --version)"
    else
        echo "[ERROR] Failed to install Chrome"
        exit 1
    fi
else
    echo "[OK] Chrome already installed: $(google-chrome --version)"
fi

# Install Chrome dependencies
echo "[INFO] Installing Chrome dependencies..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
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
        libgdk-pixbuf2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrender1 \
        libxtst6 \
        ca-certificates \
        libxext6 \
        libxi6 \
        curl \
        wget \
        unzip >/dev/null 2>&1
elif [[ "$OS" == *"Amazon Linux"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum install -y \
        nss \
        atk \
        at-spi2-atk \
        cups-libs \
        gtk3 \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXrandr \
        libXScrnSaver \
        libXtst \
        pango \
        alsa-lib \
        curl \
        wget \
        unzip >/dev/null 2>&1 || \
    sudo dnf install -y \
        nss \
        atk \
        at-spi2-atk \
        cups-libs \
        gtk3 \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXrandr \
        libXScrnSaver \
        libXtst \
        pango \
        alsa-lib \
        curl \
        wget \
        unzip >/dev/null 2>&1
fi

# Install Xvfb for virtual display
echo "[INFO] Installing Xvfb (virtual display)..."
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    sudo apt install -y xvfb >/dev/null 2>&1
elif [[ "$OS" == *"Amazon Linux"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
    sudo yum install -y xorg-x11-server-Xvfb >/dev/null 2>&1 || sudo dnf install -y xorg-x11-server-Xvfb >/dev/null 2>&1
fi

# Test Chrome basic functionality
echo "[INFO] Testing Chrome installation..."
if google-chrome --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --single-process --dump-dom about:blank >/dev/null 2>&1; then
    echo "[OK] Chrome basic test passed"
else
    echo "[ERROR] Chrome basic test failed. Check dependencies."
    exit 1
fi

# Set up project directory
PROJECT_DIR="/home/ubuntu/sociarch-scraper"
if [ "$USER" = "ec2-user" ]; then
    PROJECT_DIR="/home/ec2-user/sociarch-scraper"
fi

if [ ! -d "$PROJECT_DIR" ]; then
    echo "[INFO] Creating project directory: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Clone repository if URL is provided
    if [ -n "$1" ]; then
        echo "[INFO] Cloning repository: $1"
        git clone "$1" .
    else
        echo "[WARN] No repository URL provided. Please upload your project files to $PROJECT_DIR"
    fi
else
    echo "[INFO] Project directory already exists: $PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Create virtual environment
echo "[INFO] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip >/dev/null 2>&1

# Install requirements if file exists
if [ -f "requirements.txt" ]; then
    echo "[INFO] Installing Python dependencies..."
    pip install -r requirements.txt >/dev/null 2>&1
    echo "[OK] Python dependencies installed"
else
    echo "[WARN] requirements.txt not found. Installing basic dependencies..."
    pip install zendriver supabase python-dotenv >/dev/null 2>&1
    echo "[OK] Basic dependencies installed"
fi

# Create .env file from template if it doesn't exist
if [ ! -f ".env" ] && [ -f "env.template" ]; then
    cp env.template .env
    echo "[OK] .env file created from template"
    echo "[WARN] Please edit .env file with your Supabase credentials"
elif [ ! -f ".env" ]; then
    echo "[WARN] No .env file found. Please create one with your configuration"
fi

# Make scripts executable
chmod +x *.sh 2>/dev/null || true

# Set proper permissions for project directory
if [ "$USER" = "ubuntu" ]; then
    sudo chown -R ubuntu:ubuntu "$PROJECT_DIR"
elif [ "$USER" = "ec2-user" ]; then
    sudo chown -R ec2-user:ec2-user "$PROJECT_DIR"
fi

# Test final setup
echo "[INFO] Running final validation..."
if [ -f "validate_ec2.sh" ]; then
    ./validate_ec2.sh
else
    echo "[WARN] validate_ec2.sh not found, skipping validation"
fi

deactivate

echo ""
echo "========================================="
echo "[OK] EC2 setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Supabase credentials:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Test the setup:"
echo "   cd $PROJECT_DIR && ./validate_ec2.sh"
echo ""
echo "3. Run the scraper:"
echo "   cd $PROJECT_DIR && ./start_scraper.sh"
echo ""
echo "4. Set up daily cron job (optional):"
echo "   crontab -e"
echo "   Add: 0 6 * * * $PROJECT_DIR/daily_scraper.sh"
echo "=========================================" 