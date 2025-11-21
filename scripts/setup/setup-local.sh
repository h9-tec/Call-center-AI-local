#!/bin/bash

# Setup script for local Call Center AI development environment

set -e

echo "Setting up local Call Center AI environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
    echo -e "${GREEN}✓${NC} Environment variables loaded from .env"
else
    echo -e "${YELLOW}⚠${NC} No .env file found. Please create one from .env.example"
    exit 1
fi

# Check required services
echo -e "\n${YELLOW}Checking required services...${NC}"

# Check Docker
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed"
else
    echo -e "${RED}✗${NC} Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose is available"
else
    echo -e "${RED}✗${NC} Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION is installed"
else
    echo -e "${RED}✗${NC} Python 3 is not installed. Please install Python 3.10 or later."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo -e "\n${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$PROJECT_DIR/.venv"
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source "$PROJECT_DIR/.venv/bin/activate"
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install Python dependencies
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$PROJECT_DIR/requirements.txt"
    echo -e "${GREEN}✓${NC} Python dependencies installed"
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating necessary directories...${NC}"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/recordings"
mkdir -p "$PROJECT_DIR/data"
echo -e "${GREEN}✓${NC} Directories created"

# Check configuration
if [ -f "$PROJECT_DIR/config.yaml" ]; then
    echo -e "${GREEN}✓${NC} Configuration file exists"
else
    echo -e "${YELLOW}⚠${NC} No config.yaml found. Creating from example..."
    if [ -f "$PROJECT_DIR/config-example.yaml" ]; then
        cp "$PROJECT_DIR/config-example.yaml" "$PROJECT_DIR/config.yaml"
        echo -e "${GREEN}✓${NC} Configuration file created from example"
    else
        echo -e "${RED}✗${NC} No config example found"
    fi
fi

# Test Twilio credentials if configured
if [ ! -z "$TWILIO_ACCOUNT_SID" ] && [ ! -z "$TWILIO_AUTH_TOKEN" ]; then
    echo -e "\n${YELLOW}Testing Twilio credentials...${NC}"
    python3 -c "
from twilio.rest import Client
import os
try:
    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
    print('Account Status:', account.status)
    if account.status == 'active':
        print('✓ Twilio credentials are valid')
    else:
        print('⚠ Twilio account is not active')
except Exception as e:
    print('✗ Twilio credential test failed:', str(e))
"
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}Local environment setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "\nNext steps:"
echo -e "1. Start services: ${YELLOW}./scripts/start-services.sh${NC}"
echo -e "2. Test the setup: ${YELLOW}python run-tests.py${NC}"
echo -e "3. Make a test call: ${YELLOW}./make-call.sh +1234567890${NC}"
echo -e "\n${YELLOW}Note:${NC} Make sure all required services are running before testing."