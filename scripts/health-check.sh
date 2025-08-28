#!/bin/bash

# AndroidZen Pro - Health Check Script
# Comprehensive health monitoring for all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}
BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-androidzen_user}
POSTGRES_DB=${POSTGRES_DB:-androidzen}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

# Timeout settings
TIMEOUT=30
COMPOSE_FILE=${1:-docker-compose.yml}

# Health check results
declare -A health_status
declare -A health_messages

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if service is responsive
check_url() {
    local url="$1"
    local service_name="$2"
    local expected_status="${3:-200}"
    
    print_status "Checking $service_name at $url"
    
    local response
    local status_code
    
    if response=$(curl -s -w "%{http_code}" --connect-timeout $TIMEOUT --max-time $TIMEOUT "$url" 2>/dev/null); then
        status_code=$(echo "$response" | tail -n1)
        
        if [ "$status_code" = "$expected_status" ]; then
            print_success "$service_name is healthy (HTTP $status_code)"
            health_status["$service_name"]="healthy"
            health_messages["$service_name"]="HTTP $status_code - OK"
            return 0
        else
            print_error "$service_name returned HTTP $status_code (expected $expected_status)"
            health_status["$service_name"]="unhealthy"
            health_messages["$service_name"]="HTTP $status_code - Unexpected status"
            return 1
        fi
    else
        print_error "$service_name is not responding"
        health_status["$service_name"]="unhealthy"
        health_messages["$service_name"]="Connection failed"
        return 1
    fi
}

# Check Docker container health
check_docker_health() {
    local service_name="$1"
    
    if ! command -v docker >/dev/null 2>&1; then
        print_warning "Docker not available, skipping container health checks"
        return 1
    fi
    
    # Determine compose command
    local compose_cmd
    if docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        compose_cmd="docker-compose"
    else
        print_warning "Docker Compose not available"
        return 1
    fi
    
    print_status "Checking Docker container: $service_name"
    
    local container_status
    container_status=$($compose_cmd -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)
    
    if [ -z "$container_status" ]; then
        print_error "Container $service_name not found"
        health_status["$service_name-container"]="not_found"
        health_messages["$service_name-container"]="Container not found"
        return 1
    fi
    
    local health_status_docker
    health_status_docker=$(docker inspect --format='{{.State.Health.Status}}' "$container_status" 2>/dev/null || echo "no-health-check")
    
    case "$health_status_docker" in
        "healthy")
            print_success "Container $service_name is healthy"
            health_status["$service_name-container"]="healthy"
            health_messages["$service_name-container"]="Container healthy"
            return 0
            ;;
        "unhealthy")
            print_error "Container $service_name is unhealthy"
            health_status["$service_name-container"]="unhealthy"
            health_messages["$service_name-container"]="Container unhealthy"
            return 1
            ;;
        "starting")
            print_warning "Container $service_name is starting"
            health_status["$service_name-container"]="starting"
            health_messages["$service_name-container"]="Container starting"
            return 1
            ;;
        "no-health-check")
            local running_status
            running_status=$(docker inspect --format='{{.State.Running}}' "$container_status" 2>/dev/null)
            
            if [ "$running_status" = "true" ]; then
                print_success "Container $service_name is running (no health check configured)"
                health_status["$service_name-container"]="running"
                health_messages["$service_name-container"]="Container running"
                return 0
            else
                print_error "Container $service_name is not running"
                health_status["$service_name-container"]="stopped"
                health_messages["$service_name-container"]="Container stopped"
                return 1
            fi
            ;;
        *)
            print_warning "Container $service_name has unknown health status: $health_status_docker"
            health_status["$service_name-container"]="unknown"
            health_messages["$service_name-container"]="Unknown status: $health_status_docker"
            return 1
            ;;
    esac
}

# Check PostgreSQL database
check_postgres() {
    print_status "Checking PostgreSQL database connectivity"
    
    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
            print_success "PostgreSQL database is accessible"
            health_status["postgres"]="healthy"
            health_messages["postgres"]="Database accessible"
            
            # Check database size and connections
            if command -v psql >/dev/null 2>&1; then
                local db_info
                db_info=$(PGPASSWORD="$PGPASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT pg_database_size('$POSTGRES_DB'), numbackends FROM pg_stat_database WHERE datname='$POSTGRES_DB';" 2>/dev/null || echo "")
                
                if [ -n "$db_info" ]; then
                    print_success "Database info: $db_info"
                fi
            fi
            
            return 0
        else
            print_error "PostgreSQL database is not accessible"
            health_status["postgres"]="unhealthy"
            health_messages["postgres"]="Database connection failed"
            return 1
        fi
    else
        print_warning "pg_isready not available, skipping PostgreSQL check"
        health_status["postgres"]="skipped"
        health_messages["postgres"]="pg_isready not available"
        return 1
    fi
}

# Check Redis
check_redis() {
    print_status "Checking Redis connectivity"
    
    if command -v redis-cli >/dev/null 2>&1; then
        local redis_response
        if [ -n "$REDIS_PASSWORD" ]; then
            redis_response=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>/dev/null || echo "")
        else
            redis_response=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null || echo "")
        fi
        
        if [ "$redis_response" = "PONG" ]; then
            print_success "Redis is responding"
            health_status["redis"]="healthy"
            health_messages["redis"]="Redis responding to ping"
            
            # Get Redis info
            local redis_info
            if [ -n "$REDIS_PASSWORD" ]; then
                redis_info=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" info server 2>/dev/null | grep redis_version || echo "")
            else
                redis_info=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server 2>/dev/null | grep redis_version || echo "")
            fi
            
            if [ -n "$redis_info" ]; then
                print_success "Redis version: $(echo "$redis_info" | cut -d: -f2 | tr -d '\r')"
            fi
            
            return 0
        else
            print_error "Redis is not responding"
            health_status["redis"]="unhealthy"
            health_messages["redis"]="Redis not responding to ping"
            return 1
        fi
    else
        # Try using curl for Redis HTTP interface (if available)
        local redis_url="http://$REDIS_HOST:$((REDIS_PORT + 1000))/ping"
        if curl -s --connect-timeout 5 "$redis_url" >/dev/null 2>&1; then
            print_success "Redis HTTP interface is responding"
            health_status["redis"]="healthy"
            health_messages["redis"]="Redis HTTP interface responding"
            return 0
        else
            print_warning "redis-cli not available and Redis HTTP interface not accessible"
            health_status["redis"]="skipped"
            health_messages["redis"]="redis-cli not available"
            return 1
        fi
    fi
}

# Check system resources
check_system_resources() {
    print_status "Checking system resources"
    
    # Check disk usage
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt 90 ]; then
        print_error "Disk usage is critical: ${disk_usage}%"
        health_status["disk"]="critical"
        health_messages["disk"]="Disk usage: ${disk_usage}%"
    elif [ "$disk_usage" -gt 80 ]; then
        print_warning "Disk usage is high: ${disk_usage}%"
        health_status["disk"]="warning"
        health_messages["disk"]="Disk usage: ${disk_usage}%"
    else
        print_success "Disk usage is normal: ${disk_usage}%"
        health_status["disk"]="healthy"
        health_messages["disk"]="Disk usage: ${disk_usage}%"
    fi
    
    # Check memory usage
    if command -v free >/dev/null 2>&1; then
        local mem_usage
        mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        
        if [ "$mem_usage" -gt 90 ]; then
            print_error "Memory usage is critical: ${mem_usage}%"
            health_status["memory"]="critical"
            health_messages["memory"]="Memory usage: ${mem_usage}%"
        elif [ "$mem_usage" -gt 80 ]; then
            print_warning "Memory usage is high: ${mem_usage}%"
            health_status["memory"]="warning"
            health_messages["memory"]="Memory usage: ${mem_usage}%"
        else
            print_success "Memory usage is normal: ${mem_usage}%"
            health_status["memory"]="healthy"
            health_messages["memory"]="Memory usage: ${mem_usage}%"
        fi
    fi
    
    # Check load average
    if [ -f /proc/loadavg ]; then
        local load_avg
        load_avg=$(cut -d' ' -f1 /proc/loadavg)
        local cpu_count
        cpu_count=$(nproc 2>/dev/null || echo "1")
        
        local load_percentage
        load_percentage=$(echo "$load_avg * 100 / $cpu_count" | bc -l 2>/dev/null | cut -d. -f1 || echo "0")
        
        if [ "$load_percentage" -gt 80 ]; then
            print_warning "System load is high: $load_avg ($load_percentage%)"
            health_status["load"]="warning"
            health_messages["load"]="Load average: $load_avg"
        else
            print_success "System load is normal: $load_avg"
            health_status["load"]="healthy"
            health_messages["load"]="Load average: $load_avg"
        fi
    fi
}

# Generate health report
generate_health_report() {
    echo
    echo "======================================================"
    echo "AndroidZen Pro - Health Check Report"
    echo "======================================================"
    echo "Timestamp: $(date)"
    echo "Host: $(hostname)"
    echo
    
    local overall_status="healthy"
    local healthy_count=0
    local unhealthy_count=0
    local warning_count=0
    local total_count=0
    
    echo "Service Health Status:"
    echo "----------------------"
    
    for service in "${!health_status[@]}"; do
        local status="${health_status[$service]}"
        local message="${health_messages[$service]}"
        
        case "$status" in
            "healthy"|"running")
                printf "%-20s: %s✓ HEALTHY%s - %s\n" "$service" "$GREEN" "$NC" "$message"
                healthy_count=$((healthy_count + 1))
                ;;
            "warning")
                printf "%-20s: %s⚠ WARNING%s - %s\n" "$service" "$YELLOW" "$NC" "$message"
                warning_count=$((warning_count + 1))
                if [ "$overall_status" = "healthy" ]; then
                    overall_status="warning"
                fi
                ;;
            "unhealthy"|"critical"|"stopped")
                printf "%-20s: %s✗ UNHEALTHY%s - %s\n" "$service" "$RED" "$NC" "$message"
                unhealthy_count=$((unhealthy_count + 1))
                overall_status="unhealthy"
                ;;
            *)
                printf "%-20s: %s? UNKNOWN%s - %s\n" "$service" "$YELLOW" "$NC" "$message"
                warning_count=$((warning_count + 1))
                if [ "$overall_status" = "healthy" ]; then
                    overall_status="warning"
                fi
                ;;
        esac
        
        total_count=$((total_count + 1))
    done
    
    echo
    echo "Summary:"
    echo "--------"
    echo "Total services checked: $total_count"
    echo "Healthy services: $healthy_count"
    echo "Services with warnings: $warning_count"
    echo "Unhealthy services: $unhealthy_count"
    echo
    
    case "$overall_status" in
        "healthy")
            print_success "Overall system status: HEALTHY"
            ;;
        "warning")
            print_warning "Overall system status: WARNING - Some issues detected"
            ;;
        "unhealthy")
            print_error "Overall system status: UNHEALTHY - Critical issues detected"
            ;;
    esac
    
    echo "======================================================"
    
    # Return appropriate exit code
    case "$overall_status" in
        "healthy") return 0 ;;
        "warning") return 1 ;;
        "unhealthy") return 2 ;;
        *) return 3 ;;
    esac
}

# Main health check function
main() {
    echo "AndroidZen Pro - Comprehensive Health Check"
    echo "==========================================="
    echo "Starting health checks at $(date)"
    echo
    
    # Check services
    check_url "$BACKEND_URL/health" "backend" "200"
    check_url "$BACKEND_URL/docs" "backend-docs" "200"
    check_url "$FRONTEND_URL" "frontend" "200"
    
    # Check Docker containers (if Docker is available)
    check_docker_health "backend"
    check_docker_health "frontend"
    check_docker_health "postgres"
    check_docker_health "redis"
    
    # Check databases
    check_postgres
    check_redis
    
    # Check system resources
    check_system_resources
    
    # Generate report
    generate_health_report
}

# Handle command line arguments
case "$1" in
    --help|-h)
        echo "AndroidZen Pro Health Check Script"
        echo "Usage: $0 [OPTIONS] [COMPOSE_FILE]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick        Run quick health check (URLs only)"
        echo "  --json         Output results in JSON format"
        echo
        echo "Environment Variables:"
        echo "  FRONTEND_URL      Frontend URL (default: http://localhost:3000)"
        echo "  BACKEND_URL       Backend URL (default: http://localhost:8000)"
        echo "  POSTGRES_HOST     PostgreSQL host (default: localhost)"
        echo "  POSTGRES_PORT     PostgreSQL port (default: 5432)"
        echo "  POSTGRES_USER     PostgreSQL user (default: androidzen_user)"
        echo "  POSTGRES_DB       PostgreSQL database (default: androidzen)"
        echo "  REDIS_HOST        Redis host (default: localhost)"
        echo "  REDIS_PORT        Redis port (default: 6379)"
        echo "  REDIS_PASSWORD    Redis password (if required)"
        exit 0
        ;;
    --quick)
        echo "AndroidZen Pro - Quick Health Check"
        echo "==================================="
        
        check_url "$BACKEND_URL/health" "backend" "200"
        check_url "$FRONTEND_URL" "frontend" "200"
        
        generate_health_report
        ;;
    --json)
        # JSON output mode
        {
            echo "{"
            echo "  \"timestamp\": \"$(date -Iseconds)\","
            echo "  \"host\": \"$(hostname)\","
            echo "  \"services\": {"
            
            first=true
            for service in "${!health_status[@]}"; do
                if [ "$first" = true ]; then
                    first=false
                else
                    echo ","
                fi
                
                local status="${health_status[$service]}"
                local message="${health_messages[$service]}"
                
                echo -n "    \"$service\": {"
                echo -n "\"status\": \"$status\", "
                echo -n "\"message\": \"$message\""
                echo -n "}"
            done
            
            echo
            echo "  }"
            echo "}"
        }
        ;;
    *)
        if [ -n "$1" ] && [ "$1" != "--quick" ] && [ "$1" != "--json" ]; then
            COMPOSE_FILE="$1"
        fi
        main
        ;;
esac
