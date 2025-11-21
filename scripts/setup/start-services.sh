#!/bin/bash

# Start all local services for Call Center AI

set -e

echo "Starting Call Center AI local services..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$PROJECT_DIR")"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
    echo -e "${GREEN}✓${NC} Environment variables loaded"
fi

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2

    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $service_name is already running on port $port"
        return 0
    else
        echo -e "${YELLOW}○${NC} $service_name is not running on port $port"
        return 1
    fi
}

# Function to start docker compose services
start_docker_services() {
    local compose_file=$1
    local services=$2

    if [ -f "$compose_file" ]; then
        echo -e "${BLUE}Starting services from $compose_file...${NC}"
        if [ -z "$services" ]; then
            docker-compose -f "$compose_file" up -d
        else
            docker-compose -f "$compose_file" up -d $services
        fi
        return $?
    else
        echo -e "${YELLOW}⚠${NC} Docker compose file not found: $compose_file"
        return 1
    fi
}

echo -e "\n${YELLOW}═══════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Checking service status...${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════${NC}"

# Check Redis
if ! check_service "Redis" 6379; then
    echo -e "${BLUE}Starting Redis...${NC}"
    docker run -d --name redis-local -p 6379:6379 redis:alpine 2>/dev/null || \
    docker start redis-local 2>/dev/null || \
    echo -e "${YELLOW}⚠${NC} Could not start Redis"
    sleep 2
    check_service "Redis" 6379
fi

# Check Ollama
if ! check_service "Ollama" 11434; then
    echo -e "${BLUE}Starting Ollama...${NC}"

    # Check if Ollama is installed locally
    if command -v ollama &> /dev/null; then
        ollama serve &>/dev/null &
        sleep 3

        # Pull the model if needed
        if [ ! -z "$OLLAMA_MODEL" ]; then
            echo -e "${BLUE}Pulling Ollama model: $OLLAMA_MODEL...${NC}"
            ollama pull $OLLAMA_MODEL
        fi
    else
        # Use Docker
        docker run -d --name ollama-local \
            -p 11434:11434 \
            -v ollama:/root/.ollama \
            ollama/ollama 2>/dev/null || \
        docker start ollama-local 2>/dev/null

        sleep 3

        # Pull model in container
        if [ ! -z "$OLLAMA_MODEL" ]; then
            docker exec ollama-local ollama pull $OLLAMA_MODEL
        fi
    fi
    check_service "Ollama" 11434
fi

# Check Whisper
if ! check_service "Whisper STT" 9000; then
    echo -e "${BLUE}Starting Whisper STT service...${NC}"

    # Check if docker compose file exists
    COMPOSE_FILE="$PARENT_DIR/docker-compose.local.yaml"
    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" up -d whisper 2>/dev/null
    else
        # Run standalone
        docker run -d --name whisper-local \
            -p 9000:9000 \
            -e ASR_MODEL=base \
            onerahmet/openai-whisper-asr-webservice:latest 2>/dev/null || \
        docker start whisper-local 2>/dev/null
    fi

    sleep 5
    check_service "Whisper STT" 9000
fi

# Check Piper TTS
if ! check_service "Piper TTS" 10200; then
    echo -e "${BLUE}Starting Piper TTS service...${NC}"

    # Check if docker compose file exists
    COMPOSE_FILE="$PARENT_DIR/docker-compose.local.yaml"
    if [ -f "$COMPOSE_FILE" ]; then
        docker-compose -f "$COMPOSE_FILE" up -d piper 2>/dev/null
    else
        # Run standalone
        docker run -d --name piper-local \
            -p 10200:10200 \
            -v $PROJECT_DIR/piper-voices:/opt/piper/voices \
            rhasspy/wyoming-piper:latest \
            --voice en_US-amy-medium 2>/dev/null || \
        docker start piper-local 2>/dev/null
    fi

    sleep 3
    check_service "Piper TTS" 10200
fi

# Check Asterisk (if needed for SIP)
if [ ! -z "$USE_ASTERISK" ] && [ "$USE_ASTERISK" = "true" ]; then
    if ! check_service "Asterisk" 5060; then
        echo -e "${BLUE}Starting Asterisk PBX...${NC}"

        # Check if docker compose file exists
        COMPOSE_FILE="$PARENT_DIR/docker-compose.local.yaml"
        if [ -f "$COMPOSE_FILE" ]; then
            docker-compose -f "$COMPOSE_FILE" up -d asterisk 2>/dev/null
        else
            docker run -d --name asterisk-local \
                -p 5060:5060/udp \
                -p 5060:5060/tcp \
                -p 10000-10100:10000-10100/udp \
                -v $PROJECT_DIR/asterisk/config:/etc/asterisk \
                andrius/asterisk:alpine 2>/dev/null || \
            docker start asterisk-local 2>/dev/null
        fi

        sleep 3
        check_service "Asterisk" 5060
    fi
fi

echo -e "\n${YELLOW}═══════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Service Status Summary${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════${NC}"

# Final status check
echo -e "\n${BLUE}Checking all services...${NC}"
check_service "Redis" 6379
check_service "Ollama" 11434
check_service "Whisper STT" 9000
check_service "Piper TTS" 10200

if [ ! -z "$USE_ASTERISK" ] && [ "$USE_ASTERISK" = "true" ]; then
    check_service "Asterisk" 5060
fi

# Start the main application if requested
if [ "$1" = "--with-app" ]; then
    echo -e "\n${BLUE}Starting Call Center AI application...${NC}"

    # Activate virtual environment
    if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi

    # Start the app
    cd "$PROJECT_DIR"
    python -m uvicorn app.main:app --host 0.0.0.0 --port ${SERVER_PORT:-8080} --reload &
    APP_PID=$!

    sleep 3
    if ps -p $APP_PID > /dev/null; then
        echo -e "${GREEN}✓${NC} Application started (PID: $APP_PID)"
        echo -e "${GREEN}Access the application at: http://localhost:${SERVER_PORT:-8080}${NC}"
    else
        echo -e "${RED}✗${NC} Failed to start application"
    fi
fi

echo -e "\n${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"

# Show useful information
echo -e "\n${YELLOW}Service URLs:${NC}"
echo -e "  • Redis: localhost:6379"
echo -e "  • Ollama: http://localhost:11434"
echo -e "  • Whisper: http://localhost:9000"
echo -e "  • Piper: http://localhost:10200"

if [ ! -z "$USE_ASTERISK" ] && [ "$USE_ASTERISK" = "true" ]; then
    echo -e "  • Asterisk: sip:localhost:5060"
fi

echo -e "\n${YELLOW}To stop all services, run:${NC}"
echo -e "  ${BLUE}./scripts/stop-services.sh${NC}"

echo -e "\n${YELLOW}To view logs:${NC}"
echo -e "  ${BLUE}docker-compose logs -f [service_name]${NC}"

echo -e "\n${YELLOW}To test the setup:${NC}"
echo -e "  ${BLUE}python run-tests.py${NC}"