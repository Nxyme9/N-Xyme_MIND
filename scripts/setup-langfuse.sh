#!/usr/bin/env bash
# Langfuse Setup Script
# Installs and configures Langfuse for LLM observability
#
# Usage: bash scripts/setup-langfuse.sh [--cloud | --self-host]
#
# Options:
#   --cloud       Configure for Langfuse Cloud (default)
#   --self-host   Configure for self-hosted Langfuse

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
DEPLOYMENT_MODE="cloud"
while [[ $# -gt 0 ]]; do
    case $1 in
        --cloud)
            DEPLOYMENT_MODE="cloud"
            shift
            ;;
        --self-host)
            DEPLOYMENT_MODE="self-host"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Usage: $0 [--cloud | --self-host]"
            exit 1
            ;;
    esac
done

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_warn "Docker not found. Skipping Langfuse server setup."
        log_info "To self-host Langfuse, install Docker first:"
        echo "  https://docs.docker.com/get-docker/"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_warn "Docker is installed but not running."
        log_info "Start Docker and re-run this script."
        return 1
    fi
    
    log_info "Docker is available"
    return 0
}

setup_cloud() {
    log_info "Setting up Langfuse Cloud configuration..."
    
    # Check if .env exists
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        log_info "Found .env file, checking Langfuse variables..."
        
        if grep -q "LANGFUSE_PUBLIC_KEY" "$PROJECT_ROOT/.env" 2>/dev/null; then
            log_info "Langfuse variables already configured in .env"
        else
            log_warn "Langfuse variables not found in .env"
            log_info "Add the following to your .env file:"
            echo ""
            echo "  # Langfuse (LLM Observability)"
            echo "  LANGFUSE_PUBLIC_KEY=pk-..."
            echo "  LANGFUSE_SECRET_KEY=sk-..."
            echo "  LANGFUSE_HOST=https://cloud.langfuse.com"
            echo ""
        fi
    else
        log_warn "No .env file found. Copy .env.example to .env"
    fi
    
    log_info "Cloud setup complete!"
    log_info "1. Sign up at https://langfuse.com"
    log_info "2. Get your API keys from the dashboard"
    log_info "3. Add them to your .env file"
}

setup_self_host() {
    log_info "Setting up self-hosted Langfuse..."
    
    if ! check_docker; then
        log_warn "Cannot set up self-hosted Langfuse without Docker."
        log_info "Falling back to cloud configuration."
        setup_cloud
        return
    fi
    
    # Create docker-compose file for Langfuse
    LANGFUSE_COMPOSE="$PROJECT_ROOT/configs/langfuse/docker-compose.yml"
    mkdir -p "$(dirname "$LANGFUSE_COMPOSE")"
    
    log_info "Creating Langfuse docker-compose at $LANGFUSE_COMPOSE"
    
    cat > "$LANGFUSE_COMPOSE" << 'EOF'
version: '3.8'

services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/langfuse
      - NEXTAUTH_SECRET=your-secret-key-change-in-production
      - NEXTAUTH_URL=http://localhost:3000
    depends_on:
      - db
    volumes:
      - ./data:/app/data

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=langfuse
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
EOF

    log_info "Created docker-compose.yml"
    log_info ""
    log_info "To start Langfuse:"
    echo "  cd $PROJECT_ROOT/configs/langfuse"
    echo "  docker-compose up -d"
    log_info ""
    log_info "Langfuse will be available at http://localhost:3000"
}

main() {
    log_info "Langfuse Setup Script"
    log_info "Mode: $DEPLOYMENT_MODE"
    echo ""
    
    case $DEPLOYMENT_MODE in
        cloud)
            setup_cloud
            ;;
        self-host)
            setup_self_host
            ;;
    esac
    
    echo ""
    log_info "Setup complete!"
    log_info ""
    log_info "Next steps:"
    echo "  1. Add API keys to .env (see .env.example)"
    echo "  2. Install Langfuse SDK: pip install langfuse"
    echo "  3. Integrate in your code:"
    echo ""
    echo "     from langfuse import Langfuse"
    echo "     langfuse = Langfuse()"
    echo "     # Use langfuse.trace() to wrap LLM calls"
    echo ""
}

main "$@"
