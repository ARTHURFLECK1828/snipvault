#!/bin/bash

# SnipVault Setup Script
# This script helps you set up SnipVault quickly

set -e

echo "================================================"
echo "  SnipVault - LLM-Powered Snippet Manager"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python $python_version found"

# Check PostgreSQL
echo ""
echo "Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL is installed"
else
    echo -e "${RED}✗${NC} PostgreSQL not found. Please install PostgreSQL first."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}!${NC} Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}!${NC} .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
    echo ""
    echo -e "${YELLOW}IMPORTANT:${NC} Please edit .env file with your credentials:"
    echo "  1. DATABASE_URL - PostgreSQL connection string"
    echo "  2. PINECONE_API_KEY - Your Pinecone API key"
    echo "  3. PINECONE_ENVIRONMENT - Your Pinecone environment"
    echo "  4. GOOGLE_API_KEY - Your Google Gemini API key"
    echo ""
    echo "After configuring .env, run:"
    echo "  source venv/bin/activate"
    echo "  python main.py init"
    exit 0
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Ask if user wants to initialize databases
echo ""
read -p "Do you want to initialize databases now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Initializing databases..."
    python main.py init
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  SnipVault setup complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Add a snippet: python main.py add <title> <code> --lang <language>"
echo "  3. Search: python main.py search <query>"
echo "  4. List all: python main.py list"
echo ""
echo "For help: python main.py --help"
