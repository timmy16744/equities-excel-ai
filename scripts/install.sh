#!/bin/bash
set -e

# Equities AI Installation Script
# This script sets up a production-ready installation of Equities AI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker 20.0+ first."
        exit 1
    fi

    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+' | head -1)
    log_info "Docker version: $DOCKER_VERSION"

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "docker-compose is not installed. Please install docker-compose first."
        exit 1
    fi

    # Check available memory (minimum 4GB recommended)
    if [ -f /proc/meminfo ]; then
        TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        TOTAL_MEM_GB=$((TOTAL_MEM / 1024 / 1024))
        if [ "$TOTAL_MEM_GB" -lt 4 ]; then
            log_warning "System has ${TOTAL_MEM_GB}GB RAM. Recommended: 4GB minimum."
        else
            log_info "System memory: ${TOTAL_MEM_GB}GB"
        fi
    fi

    log_success "Prerequisites check passed"
}

# Generate secure secrets
generate_secrets() {
    log_info "Generating secure secrets..."

    JWT_SECRET=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)

    log_success "Secrets generated"
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."

    ENV_FILE="$PROJECT_DIR/.env"

    if [ -f "$ENV_FILE" ]; then
        log_warning ".env file already exists. Creating backup..."
        cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    cat > "$ENV_FILE" << EOF
# Equities AI Production Configuration
# Generated on $(date)

# Database
DATABASE_URL=postgresql+asyncpg://equities:${DB_PASSWORD}@postgres:5432/equities_ai
POSTGRES_USER=equities
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=equities_ai

# Authentication
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://redis:6379/0

# CORS - Update with your domain
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=production

# Application
APP_VERSION=1.0.0
EOF

    chmod 600 "$ENV_FILE"
    log_success "Environment file created"
}

# Build and start services
start_services() {
    log_info "Building and starting services..."

    cd "$PROJECT_DIR"

    # Use production compose file if it exists
    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml up -d --build
    else
        docker-compose up -d --build
    fi

    log_info "Waiting for services to be healthy..."
    sleep 10

    log_success "Services started"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_DIR"

    # Run migrations inside the container
    docker-compose exec -T api python -m alembic -c backend/alembic.ini upgrade head || {
        log_warning "Migration via exec failed, trying direct..."
        # If exec fails, try running in new container
        docker-compose run --rm api python -m alembic -c backend/alembic.ini upgrade head
    }

    log_success "Migrations completed"
}

# Create admin user
create_admin_user() {
    log_info "Creating admin user..."

    read -p "Enter admin email: " ADMIN_EMAIL
    read -s -p "Enter admin password (min 8 chars): " ADMIN_PASSWORD
    echo

    if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
        log_error "Password must be at least 8 characters"
        exit 1
    fi

    cd "$PROJECT_DIR"

    # Create admin user via Python script
    docker-compose exec -T api python << EOF
import asyncio
from backend.database import get_db, engine
from backend.utils.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

async def create_admin():
    async with AsyncSession(engine) as db:
        auth = AuthService(db)
        existing = await auth.get_user_by_email("${ADMIN_EMAIL}")
        if existing:
            print("User already exists")
            return
        user = await auth.create_user(
            email="${ADMIN_EMAIL}",
            password="${ADMIN_PASSWORD}",
            full_name="Admin",
            is_admin=True
        )
        print(f"Admin user created: {user.email}")

asyncio.run(create_admin())
EOF

    log_success "Admin user created"
}

# Display final information
display_info() {
    echo
    echo "=============================================="
    log_success "Equities AI Installation Complete!"
    echo "=============================================="
    echo
    echo "Access the application:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Health:   http://localhost:8000/health"
    echo
    echo "Useful commands:"
    echo "  - View logs:    ./scripts/logs.sh"
    echo "  - Stop:         ./scripts/stop.sh"
    echo "  - Start:        ./scripts/start.sh"
    echo "  - Backup DB:    ./scripts/backup.sh"
    echo
    echo "Configuration file: .env"
    echo
    log_warning "Remember to update CORS_ORIGINS in .env for production!"
    echo
}

# Main installation flow
main() {
    echo "=============================================="
    echo "  Equities AI Installation"
    echo "=============================================="
    echo

    check_prerequisites
    generate_secrets
    create_env_file
    start_services
    run_migrations

    read -p "Create admin user now? (y/n): " CREATE_ADMIN
    if [ "$CREATE_ADMIN" = "y" ] || [ "$CREATE_ADMIN" = "Y" ]; then
        create_admin_user
    fi

    display_info
}

main "$@"
