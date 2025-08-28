#!/bin/bash

# AndroidZen Pro - Development Deployment Script
# This script sets up and starts the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    
    if docker compose version &> /dev/null; then
        COMPOSE_COMMAND="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_COMMAND="docker-compose"
    else
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker Compose is available: $COMPOSE_COMMAND"
}

# Create .env file from .env.example if it doesn't exist
setup_env_file() {
    print_status "Setting up environment file..."
    
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_success ".env file created from .env.example"
        print_warning "Please review and update .env file with your specific configuration"
    else
        print_success ".env file already exists"
    fi
}

# Create required directories
create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p database/init
    mkdir -p database/backups
    
    print_success "Required directories created"
}

# Build and start services
start_services() {
    print_status "Building and starting development services..."
    
    # Pull latest images
    $COMPOSE_COMMAND pull
    
    # Build services
    $COMPOSE_COMMAND build --no-cache
    
    # Start services
    $COMPOSE_COMMAND up -d
    
    print_success "Services started successfully"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    # Wait for database
    print_status "Waiting for PostgreSQL..."
    timeout 60s bash -c 'until $COMPOSE_COMMAND exec -T postgres pg_isready -U ${POSTGRES_USER:-androidzen_user} -d ${POSTGRES_DB:-androidzen}; do sleep 2; done'
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    timeout 30s bash -c 'until $COMPOSE_COMMAND exec -T redis redis-cli ping; do sleep 2; done'
    
    # Wait for backend
    print_status "Waiting for Backend API..."
    timeout 90s bash -c 'until curl -f http://localhost:8000/health; do sleep 5; done'
    
    # Wait for frontend
    print_status "Waiting for Frontend..."
    timeout 60s bash -c 'until curl -f http://localhost:3000/; do sleep 5; done'
    
    print_success "All services are healthy"
}

# Display service status
show_status() {
    print_status "Service Status:"
    $COMPOSE_COMMAND ps
    
    echo
    print_success "Development environment is ready!"
    echo
    print_status "Access your application:"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo
    print_status "Optional services (use --profile tools):"
    echo "  pgAdmin: http://localhost:8080"
    echo "  Redis Commander: http://localhost:8081"
    echo
    print_status "To view logs: $COMPOSE_COMMAND logs -f [service_name]"
    print_status "To stop services: $COMPOSE_COMMAND down"
}

# Main execution
main() {
    echo "======================================================"
    echo "AndroidZen Pro - Development Deployment"
    echo "======================================================"
    echo
    
    check_docker
    check_docker_compose
    setup_env_file
    create_directories
    
    # Parse command line arguments
    PROFILES=""
    for arg in "$@"; do
        case $arg in
            --tools)
                PROFILES="--profile tools"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --tools    Start optional tools (pgAdmin, Redis Commander)"
                echo "  --help     Show this help message"
                exit 0
                ;;
        esac
    done
    
    # Export compose command for use in functions
    export COMPOSE_COMMAND
    
    start_services
    wait_for_services
    show_status
    
    echo
    print_success "Development environment deployment completed successfully!"
}

# Run main function with all arguments
main "$@"
