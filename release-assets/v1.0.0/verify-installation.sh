#!/bin/bash
# AndroidZen Pro v1.0.0 - Installation Verification Script
# This script verifies that AndroidZen Pro has been installed correctly

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
TIMEOUT=30

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AndroidZen Pro v1.0.0 Installation Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [[ $status == "OK" ]]; then
        echo -e "✅ ${GREEN}$message${NC}"
    elif [[ $status == "WARNING" ]]; then
        echo -e "⚠️  ${YELLOW}$message${NC}"
    else
        echo -e "❌ ${RED}$message${NC}"
    fi
}

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local expected_status=$2
    local description=$3
    
    echo -n "Checking $description... "
    if response=$(curl -s -w "%{http_code}" -o /dev/null --connect-timeout $TIMEOUT "$url" 2>/dev/null); then
        if [[ $response == $expected_status ]]; then
            print_status "OK" "$description is responding correctly (HTTP $response)"
            return 0
        else
            print_status "ERROR" "$description returned HTTP $response (expected $expected_status)"
            return 1
        fi
    else
        print_status "ERROR" "$description is not responding"
        return 1
    fi
}

# Function to check service health
check_service_health() {
    local service_name=$1
    echo -n "Checking $service_name status... "
    
    if docker compose ps --format json | grep -q "\"Service\":\"$service_name\".*\"Status\":\"running\""; then
        print_status "OK" "$service_name is running"
        return 0
    else
        print_status "ERROR" "$service_name is not running"
        return 1
    fi
}

# Function to check API health with detailed response
check_api_health() {
    echo -n "Checking API health endpoint... "
    if response=$(curl -s --connect-timeout $TIMEOUT "$BASE_URL/health" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"healthy"'; then
            print_status "OK" "API health check passed"
            echo -e "   ${BLUE}Response:${NC} $response"
            return 0
        else
            print_status "ERROR" "API health check failed"
            echo -e "   ${RED}Response:${NC} $response"
            return 1
        fi
    else
        print_status "ERROR" "API health endpoint is not responding"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    echo -n "Checking database connectivity... "
    if docker compose exec -T postgres pg_isready -q 2>/dev/null; then
        print_status "OK" "PostgreSQL database is ready"
        return 0
    else
        # Try SQLite for development setup
        if docker compose exec -T backend python -c "from backend.core.database import engine; engine.connect()" 2>/dev/null; then
            print_status "OK" "Database connection successful"
            return 0
        else
            print_status "ERROR" "Database is not accessible"
            return 1
        fi
    fi
}

# Function to check Redis connectivity
check_redis() {
    echo -n "Checking Redis connectivity... "
    if docker compose exec -T redis redis-cli ping | grep -q "PONG" 2>/dev/null; then
        print_status "OK" "Redis is responding"
        return 0
    else
        print_status "WARNING" "Redis may not be running (optional for basic functionality)"
        return 1
    fi
}

# Function to check WebSocket connectivity
check_websocket() {
    echo -n "Checking WebSocket endpoint... "
    # For now, just check if the stats endpoint is accessible
    if response=$(curl -s --connect-timeout $TIMEOUT "$BASE_URL/ws/stats" 2>/dev/null); then
        if echo "$response" | grep -q "websocket_stats"; then
            print_status "OK" "WebSocket functionality is available"
            return 0
        else
            print_status "WARNING" "WebSocket endpoint responded but may not be fully functional"
            return 1
        fi
    else
        print_status "ERROR" "WebSocket endpoint is not responding"
        return 1
    fi
}

# Main verification process
main() {
    local errors=0
    local warnings=0
    
    echo -e "${YELLOW}Starting installation verification...${NC}"
    echo
    
    # Check if Docker is running
    echo -e "${BLUE}1. Docker Environment${NC}"
    if docker version >/dev/null 2>&1; then
        print_status "OK" "Docker is running"
    else
        print_status "ERROR" "Docker is not running or not accessible"
        ((errors++))
        echo -e "${RED}Please start Docker and try again${NC}"
        exit 1
    fi
    
    if docker compose version >/dev/null 2>&1; then
        print_status "OK" "Docker Compose is available"
    else
        print_status "ERROR" "Docker Compose is not available"
        ((errors++))
    fi
    echo
    
    # Check Docker services
    echo -e "${BLUE}2. Container Services${NC}"
    check_service_health "backend" || ((errors++))
    check_service_health "frontend" || ((errors++))
    check_service_health "postgres" || ((warnings++))
    check_service_health "redis" || ((warnings++))
    echo
    
    # Check database connectivity
    echo -e "${BLUE}3. Database Connectivity${NC}"
    check_database || ((errors++))
    echo
    
    # Check Redis connectivity
    echo -e "${BLUE}4. Cache Service${NC}"
    check_redis || ((warnings++))
    echo
    
    # Check API endpoints
    echo -e "${BLUE}5. API Endpoints${NC}"
    check_api_health || ((errors++))
    check_endpoint "$BASE_URL/" 200 "API root endpoint" || ((errors++))
    check_endpoint "$BASE_URL/docs" 200 "API documentation" || ((errors++))
    check_endpoint "$BASE_URL/openapi.json" 200 "OpenAPI schema" || ((errors++))
    echo
    
    # Check WebSocket functionality
    echo -e "${BLUE}6. WebSocket Functionality${NC}"
    check_websocket || ((warnings++))
    echo
    
    # Check frontend
    echo -e "${BLUE}7. Frontend Application${NC}"
    check_endpoint "$FRONTEND_URL" 200 "Frontend application" || ((errors++))
    echo
    
    # Additional API endpoint checks
    echo -e "${BLUE}8. API Functionality${NC}"
    echo -n "Checking API authentication endpoints... "
    if curl -s --connect-timeout $TIMEOUT "$BASE_URL/api/auth/login" -X POST -H "Content-Type: application/json" -d '{}' | grep -q "detail"; then
        print_status "OK" "Authentication endpoints are responding"
    else
        print_status "WARNING" "Authentication endpoints may not be fully configured"
        ((warnings++))
    fi
    
    echo -n "Checking API device endpoints... "
    if curl -s --connect-timeout $TIMEOUT "$BASE_URL/api/devices/" | grep -q -E "(Unauthorized|devices)"; then
        print_status "OK" "Device management endpoints are responding"
    else
        print_status "WARNING" "Device management endpoints may not be fully configured"
        ((warnings++))
    fi
    echo
    
    # Final summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Verification Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [[ $errors -eq 0 && $warnings -eq 0 ]]; then
        print_status "OK" "All checks passed! AndroidZen Pro is ready to use."
        echo
        echo -e "${GREEN}🎉 Installation verified successfully!${NC}"
        echo
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Open the frontend: $FRONTEND_URL"
        echo "2. Access API documentation: $BASE_URL/docs"
        echo "3. Create your first admin user (see DEPLOYMENT.md)"
        echo
    elif [[ $errors -eq 0 ]]; then
        print_status "WARNING" "Installation completed with $warnings warning(s)."
        echo
        echo -e "${YELLOW}⚠️  Installation has minor issues but should be functional.${NC}"
        echo "Consider reviewing the warnings above."
        echo
    else
        print_status "ERROR" "Installation verification failed with $errors error(s) and $warnings warning(s)."
        echo
        echo -e "${RED}❌ Installation verification failed!${NC}"
        echo
        echo -e "${BLUE}Troubleshooting steps:${NC}"
        echo "1. Check service logs: docker compose logs"
        echo "2. Restart services: docker compose restart"
        echo "3. Review configuration in .env file"
        echo "4. Check DEPLOYMENT.md for detailed troubleshooting"
        echo
        exit 1
    fi
    
    # Show useful endpoints
    echo -e "${BLUE}Access Points:${NC}"
    echo "• Frontend Application: $FRONTEND_URL"
    echo "• API Documentation: $BASE_URL/docs"
    echo "• API Health Check: $BASE_URL/health"
    echo "• API Root: $BASE_URL/"
    echo
    
    echo -e "${GREEN}Installation verification completed!${NC}"
}

# Run main function
main "$@"
