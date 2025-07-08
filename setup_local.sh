#!/bin/bash
# Local Development Setup Script
# Run this script to set up the movie scraper for local development

echo "🚀 Setting up Movie Scraper for Local Development"
echo "=" * 50

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔄 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "🔄 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔄 Creating .env file from template..."
    cp env.template .env
    echo "✅ .env file created from template"
    echo "⚠️  Please edit .env file and add your Supabase credentials"
else
    echo "✅ .env file already exists"
fi

# Test setup
echo "🔄 Testing setup..."
python test_setup.py

echo ""
echo "✅ Local setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file and add your Supabase credentials"
echo "2. Test the scraper: python main.py"
echo "3. For headless testing: export HEADLESS_MODE=true && python main.py" 