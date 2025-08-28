#!/bin/bash

# AndroidZen Pro - Production Deployment Script
# This script deploys the application to production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
APP_NAME="androidzen-pro"
BACKUP_DIR="./database/backups"
LOG_DIR="./logs"

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

# Check if running as root (required for some production operations)
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Make sure this is intended for production deployment."
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        exit 1
    fi
    
    # Check Docker Compose
    if docker compose version &> /dev/null; then
        COMPOSE_COMMAND="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_COMMAND="docker-compose"
    else
        print_error "Docker Compose is not available."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Validate environment configuration
validate_env() {
    print_status "Validating environment configuration..."
    
    if [ ! -f .env ]; then
        print_error ".env file not found. Please create it from .env.example and configure for production."
        exit 1
    fi
    
    # Source the .env file
    set -o allexport
    source .env
    set +o allexport
    
    # Check critical production variables
    required_vars=(
        "POSTGRES_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "REDIS_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_error "Required environment variable $var is not set."
            exit 1
        fi
    done
    
    # Check if using default/weak passwords
    if [ "$POSTGRES_PASSWORD" = "dev_password" ] || [ "$POSTGRES_PASSWORD" = "your_secure_password" ]; then
        print_error "Default PostgreSQL password detected. Please set a strong password."
        exit 1
    fi
    
    if [ "$SECRET_KEY" = "your-secret-key-here-change-this-in-production" ]; then
        print_error "Default SECRET_KEY detected. Please set a secure secret key."
        exit 1
    fi
    
    print_success "Environment validation passed"
}

# Create production directories
setup_directories() {
    print_status "Setting up production directories..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "./ssl"
    mkdir -p "./monitoring"
    mkdir -p "./database/init"
    
    # Set proper permissions
    chmod 755 "$BACKUP_DIR" "$LOG_DIR"
    
    print_success "Production directories created"
}

# Backup existing data (if any)
backup_data() {
    if [ "$1" = "--skip-backup" ]; then
        print_warning "Skipping data backup as requested"
        return
    fi
    
    print_status "Creating backup of existing data..."
    
    # Check if there are existing containers
    if $COMPOSE_COMMAND -f $COMPOSE_FILE ps -q postgres &> /dev/null; then
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        BACKUP_FILE="$BACKUP_DIR/backup_pre_deploy_$TIMESTAMP.sql"
        
        print_status "Backing up database to $BACKUP_FILE"
        $COMPOSE_COMMAND -f $COMPOSE_FILE exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"
        
        if [ $? -eq 0 ]; then
            print_success "Database backup created successfully"
        else
            print_error "Database backup failed"
            exit 1
        fi
    else
        print_warning "No existing database found to backup"
    fi
}

# Pull and build images
build_images() {
    print_status "Building production images..."
    
    # Set build arguments
    BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    VERSION=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "dev")
    
    # Pull base images
    $COMPOSE_COMMAND -f $COMPOSE_FILE pull postgres redis
    
    # Build application images
    $COMPOSE_COMMAND -f $COMPOSE_FILE build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        --no-cache backend frontend
    
    print_success "Images built successfully"
}

# Deploy services
deploy_services() {
    print_status "Deploying production services..."
    
    # Parse deployment profiles
    PROFILES=""
    for arg in "$@"; do
        case $arg in
            --monitoring)
                PROFILES="$PROFILES --profile monitoring"
                ;;
            --backup)
                PROFILES="$PROFILES --profile backup"
                ;;
        esac
    done
    
    # Stop existing services
    $COMPOSE_COMMAND -f $COMPOSE_FILE down
    
    # Start services
    $COMPOSE_COMMAND -f $COMPOSE_FILE up -d $PROFILES
    
    print_success "Services deployed successfully"
}

# Wait for services to be healthy
wait_for_health() {
    print_status "Waiting for services to become healthy..."
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        healthy_services=0
        total_services=0
        
        # Check each service health
        services=($($COMPOSE_COMMAND -f $COMPOSE_FILE ps --services))
        
        for service in "${services[@]}"; do
            total_services=$((total_services + 1))
            health=$($COMPOSE_COMMAND -f $COMPOSE_FILE ps --format json | jq -r ".[] | select(.Service == \"$service\") | .Health")
            
            if [ "$health" = "healthy" ] || [ "$health" = "null" ]; then
                healthy_services=$((healthy_services + 1))
            fi
        done
        
        if [ $healthy_services -eq $total_services ]; then
            print_success "All services are healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        print_status "Waiting for services... ($attempt/$max_attempts)"
        sleep 10
    done
    
    print_error "Services did not become healthy within timeout"
    exit 1
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    $COMPOSE_COMMAND -f $COMPOSE_FILE exec -T backend alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_success "Database migrations completed"
    else
        print_error "Database migrations failed"
        exit 1
    fi
}

# Validate deployment
validate_deployment() {
    print_status "Validating deployment..."
    
    # Check if services are running
    if ! $COMPOSE_COMMAND -f $COMPOSE_FILE ps | grep -q "Up"; then
        print_error "No services are running"
        exit 1
    fi
    
    # Test backend health endpoint
    if curl -f -s http://localhost:8000/health > /dev/null; then
        print_success "Backend health check passed"
    else
        print_error "Backend health check failed"
        exit 1
    fi
    
    # Test frontend (if not using external load balancer)
    if curl -f -s http://localhost:80/ > /dev/null; then
        print_success "Frontend health check passed"
    else
        print_warning "Frontend health check failed (may be normal if using external load balancer)"
    fi
    
    print_success "Deployment validation completed"
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    $COMPOSE_COMMAND -f $COMPOSE_FILE ps
    
    echo
    print_success "Production deployment completed!"
    echo
    print_status "Services:"
    echo "  Frontend: http://$(hostname):80 (or your configured domain)"
    echo "  Backend API: http://$(hostname):8000/docs"
    echo
    print_status "Management commands:"
    echo "  View logs: $COMPOSE_COMMAND -f $COMPOSE_FILE logs -f [service_name]"
    echo "  Stop services: $COMPOSE_COMMAND -f $COMPOSE_FILE down"
    echo "  Scale services: $COMPOSE_COMMAND -f $COMPOSE_FILE up -d --scale backend=3"
    echo
    print_status "Backup location: $BACKUP_DIR"
    print_status "Logs location: $LOG_DIR"
}

# Cleanup old images and containers
cleanup() {
    if [ "$1" = "--cleanup" ]; then
        print_status "Cleaning up old images and containers..."
        docker system prune -f
        docker image prune -f
        print_success "Cleanup completed"
    fi
}

# Main function
main() {
    echo "======================================================"
    echo "AndroidZen Pro - Production Deployment"
    echo "======================================================"
    echo
    
    # Parse command line arguments
    SKIP_BACKUP=false
    ENABLE_MONITORING=false
    ENABLE_BACKUP=false
    CLEANUP_AFTER=false
    
    for arg in "$@"; do
        case $arg in
            --skip-backup)
                SKIP_BACKUP=true
                ;;
            --monitoring)
                ENABLE_MONITORING=true
                ;;
            --backup)
                ENABLE_BACKUP=true
                ;;
            --cleanup)
                CLEANUP_AFTER=true
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-backup  Skip database backup before deployment"
                echo "  --monitoring   Enable monitoring services (Prometheus, Grafana)"
                echo "  --backup       Enable automated backup service"
                echo "  --cleanup      Clean up old Docker images after deployment"
                echo "  --help         Show this help message"
                exit 0
                ;;
        esac
    done
    
    check_permissions
    check_prerequisites
    validate_env
    setup_directories
    
    if [ "$SKIP_BACKUP" = false ]; then
        backup_data
    else
        backup_data --skip-backup
    fi
    
    build_images
    deploy_services "$@"
    wait_for_health
    run_migrations
    validate_deployment
    show_status
    
    if [ "$CLEANUP_AFTER" = true ]; then
        cleanup --cleanup
    fi
    
    echo
    print_success "Production deployment completed successfully!"
    print_warning "Please verify all services are working correctly and update your DNS/load balancer settings."
}

# Run main function with all arguments
main "$@"
