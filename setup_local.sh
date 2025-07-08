#!/bin/bash

# Local Development Setup Script for Movie Scraper
echo "Setting up Movie Scraper for Local Development"
echo "==============================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[FAIL] Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "[OK] Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt
echo "[OK] Dependencies installed"

# Copy environment template if .env doesn't exist
if [ ! -f ".env" ]; then
    cp env.template .env
    echo "[OK] .env file created from template"
    echo "[WARN] Please edit .env file and add your Supabase credentials"
else
    echo "[OK] .env file already exists"
fi

# Make scripts executable
chmod +x *.sh

deactivate

echo ""
echo "[OK] Local setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Supabase credentials"
echo "2. Test setup: python test_setup.py"
echo "3. Run scraper: python main.py" 