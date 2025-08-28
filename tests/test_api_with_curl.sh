#!/bin/bash

# AndroidZen Pro API Testing with cURL
# Tests all REST API endpoints using curl commands
# This script follows the requirements from Step 10: Point 12: API and Integration Testing

set -e

# Configuration
BASE_URL="http://localhost:8000"
TIMEOUT=15
PASS_COUNT=0
FAIL_COUNT=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Generate random test user data
TEST_USER="testuser_$(date +%s)"
TEST_EMAIL="${TEST_USER}@example.com"
TEST_PASSWORD="TestPassword123!"

# Function to print headers
print_header() {
    echo -e "\n${CYAN}${BOLD}=================================="
    echo -e " $1"
    echo -e "==================================${NC}"
}

# Function to print test results
print_result() {
    local test_name="$1"
    local success="$2"
    local details="$3"
    
    if [ "$success" = "true" ]; then
        echo -e "${GREEN}PASS${NC} $test_name"
        ((PASS_COUNT++))
    else
        echo -e "${RED}FAIL${NC} $test_name"
        ((FAIL_COUNT++))
    fi
    
    if [ -n "$details" ]; then
        echo "    $details"
    fi
}

# Function to make curl requests with timeout
make_curl_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local headers="$4"
    local expected_status="$5"
    
    local url="${BASE_URL}${endpoint}"
    local curl_args=("-s" "-w" "%{http_code}" "--connect-timeout" "$TIMEOUT" "--max-time" "$TIMEOUT")
    
    if [ -n "$headers" ]; then
        while IFS= read -r header; do
            curl_args+=("-H" "$header")
        done <<< "$headers"
    fi
    
    case "$method" in
        "GET")
            response=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000")
            ;;
        "POST")
            if [ -n "$data" ]; then
                curl_args+=("-H" "Content-Type: application/json" "-d" "$data")
            fi
            response=$(curl "${curl_args[@]}" -X POST "$url" 2>/dev/null || echo "000")
            ;;
        "PUT")
            if [ -n "$data" ]; then
                curl_args+=("-H" "Content-Type: application/json" "-d" "$data")
            fi
            response=$(curl "${curl_args[@]}" -X PUT "$url" 2>/dev/null || echo "000")
            ;;
        "DELETE")
            response=$(curl "${curl_args[@]}" -X DELETE "$url" 2>/dev/null || echo "000")
            ;;
        "OPTIONS")
            response=$(curl "${curl_args[@]}" -X OPTIONS "$url" 2>/dev/null || echo "000")
            ;;
    esac
    
    # Extract status code (last 3 characters)
    status_code="${response: -3}"
    response_body="${response%???}"
    
    # Check if status code matches expected
    if [[ " $expected_status " == *" $status_code "* ]]; then
        echo "true|$status_code|$response_body"
    else
        echo "false|$status_code|$response_body"
    fi
}

# Wait for server to be ready
wait_for_server() {
    print_header "Waiting for Server"
    
    echo "Checking if server is ready..."
    for i in {1..30}; do
        result=$(make_curl_request "GET" "/health" "" "" "200 503")
        IFS='|' read -r success status_code response <<< "$result"
        
        if [ "$success" = "true" ]; then
            print_result "Server availability" "true" "Server is ready (status: $status_code)"
            return 0
        fi
        
        if [ $((i % 5)) -eq 0 ]; then
            echo "Attempt $i/30..."
        fi
        sleep 2
    done
    
    print_result "Server availability" "false" "Server not responding after 60 seconds"
    return 1
}

# Test public endpoints
test_public_endpoints() {
    print_header "Testing Public Endpoints"
    
    # Test root endpoint
    result=$(make_curl_request "GET" "/" "" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "Root endpoint (/)" "$success" "Status: $status_code"
    
    # Test health check
    result=$(make_curl_request "GET" "/health" "" "" "200 503")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "Health check (/health)" "$success" "Status: $status_code"
    
    # Test OpenAPI docs
    result=$(make_curl_request "GET" "/docs" "" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "OpenAPI docs (/docs)" "$success" "Status: $status_code"
    
    # Test ReDoc
    result=$(make_curl_request "GET" "/redoc" "" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "ReDoc (/redoc)" "$success" "Status: $status_code"
    
    # Test OpenAPI schema
    result=$(make_curl_request "GET" "/openapi.json" "" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "OpenAPI schema" "$success" "Status: $status_code"
}

# Test authentication flow
test_authentication() {
    print_header "Testing Authentication Flow"
    
    # Test user registration
    register_data="{
        \"username\": \"$TEST_USER\",
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\",
        \"full_name\": \"Test User\"
    }"
    
    result=$(make_curl_request "POST" "/api/auth/register" "$register_data" "" "200 201")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "User registration" "$success" "Status: $status_code"
    
    if [ "$success" != "true" ]; then
        echo "Registration failed, skipping login tests"
        return
    fi
    
    # Test user login
    login_data="{
        \"username\": \"$TEST_USER\",
        \"password\": \"$TEST_PASSWORD\"
    }"
    
    result=$(make_curl_request "POST" "/api/auth/login" "$login_data" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "User login" "$success" "Status: $status_code"
    
    if [ "$success" = "true" ] && [ -n "$response" ]; then
        # Extract JWT token from response
        JWT_TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        REFRESH_TOKEN=$(echo "$response" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)
        
        if [ -n "$JWT_TOKEN" ]; then
            echo "    JWT token obtained: ${JWT_TOKEN:0:50}..."
            
            # Test protected endpoint with token
            auth_header="Authorization: Bearer $JWT_TOKEN"
            result=$(make_curl_request "GET" "/api/auth/me" "" "$auth_header" "200")
            IFS='|' read -r success status_code response <<< "$result"
            print_result "Get current user" "$success" "Status: $status_code"
            
            # Test token refresh
            if [ -n "$REFRESH_TOKEN" ]; then
                refresh_data="{\"refresh_token\": \"$REFRESH_TOKEN\"}"
                result=$(make_curl_request "POST" "/api/auth/refresh" "$refresh_data" "" "200")
                IFS='|' read -r success status_code response <<< "$result"
                print_result "Token refresh" "$success" "Status: $status_code"
            fi
            
        else
            print_result "JWT token extraction" "false" "No token found in response"
        fi
    fi
    
    # Test invalid login
    invalid_login="{
        \"username\": \"invalid_user\",
        \"password\": \"wrong_password\"
    }"
    
    result=$(make_curl_request "POST" "/api/auth/login" "$invalid_login" "" "401")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "Invalid credentials rejection" "$success" "Status: $status_code (should be 401)"
}

# Test protected endpoints
test_protected_endpoints() {
    print_header "Testing Protected Endpoints"
    
    if [ -z "$JWT_TOKEN" ]; then
        print_result "Protected endpoints" "false" "No JWT token available"
        return
    fi
    
    auth_header="Authorization: Bearer $JWT_TOKEN"
    
    # Test various protected endpoints
    endpoints=(
        "/api/devices/|Devices API"
        "/api/storage/stats|Storage API"
        "/api/ai/health|AI Analytics API"
        "/api/security/events|Security API"
        "/api/network/status|Network API"
        "/api/settings/|Settings API"
        "/api/reports/|Reports API"
        "/api/monitoring/health|Monitoring API"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS='|' read -r endpoint name <<< "$endpoint_info"
        result=$(make_curl_request "GET" "$endpoint" "" "$auth_header" "200 404")
        IFS='|' read -r success status_code response <<< "$result"
        print_result "$name" "$success" "Status: $status_code"
    done
    
    # Test unauthorized access
    result=$(make_curl_request "GET" "/api/devices/" "" "" "401 403")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "Unauthorized access rejection" "$success" "Status: $status_code (should be 401/403)"
}

# Test CORS configuration
test_cors() {
    print_header "Testing CORS Configuration"
    
    cors_headers="Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization"
    
    result=$(make_curl_request "OPTIONS" "/" "" "$cors_headers" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "CORS preflight" "$success" "Status: $status_code"
    
    # Test CORS headers in actual response
    cors_response=$(curl -s -I -H "Origin: http://localhost:3000" "${BASE_URL}/" 2>/dev/null || echo "")
    if echo "$cors_response" | grep -i "access-control-allow-origin" >/dev/null; then
        print_result "CORS headers present" "true" "CORS headers found in response"
    else
        print_result "CORS headers present" "false" "No CORS headers found"
    fi
}

# Test file upload/download
test_file_operations() {
    print_header "Testing File Upload/Download"
    
    if [ -z "$JWT_TOKEN" ]; then
        print_result "File operations" "false" "No JWT token available"
        return
    fi
    
    # Create a test file
    echo "This is a test file for upload testing" > test_upload.txt
    
    auth_header="Authorization: Bearer $JWT_TOKEN"
    
    # Test file upload (note: this might not exist in the API yet)
    upload_response=$(curl -s -w "%{http_code}" -H "$auth_header" \
        -F "file=@test_upload.txt" \
        "${BASE_URL}/api/files/upload" 2>/dev/null || echo "000")
    
    upload_status="${upload_response: -3}"
    
    if [ "$upload_status" = "200" ] || [ "$upload_status" = "201" ]; then
        print_result "File upload" "true" "Status: $upload_status"
    elif [ "$upload_status" = "404" ]; then
        print_result "File upload" "false" "Upload endpoint not implemented (404)"
    else
        print_result "File upload" "false" "Status: $upload_status"
    fi
    
    # Clean up test file
    rm -f test_upload.txt
}

# Test WebSocket endpoints
test_websocket_endpoints() {
    print_header "Testing WebSocket Related Endpoints"
    
    # Test WebSocket stats endpoint (public)
    result=$(make_curl_request "GET" "/ws/stats" "" "" "200")
    IFS='|' read -r success status_code response <<< "$result"
    print_result "WebSocket stats endpoint" "$success" "Status: $status_code"
}

# Test admin endpoints
test_admin_endpoints() {
    print_header "Testing Admin Endpoints"
    
    # Try to login as admin
    admin_login="{
        \"username\": \"admin\",
        \"password\": \"admin123\"
    }"
    
    result=$(make_curl_request "POST" "/api/auth/login" "$admin_login" "" "200 401")
    IFS='|' read -r success status_code response <<< "$result"
    
    if [ "$success" = "true" ] && [ -n "$response" ]; then
        ADMIN_TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        
        if [ -n "$ADMIN_TOKEN" ]; then
            print_result "Admin login" "true" "Admin authentication successful"
            
            admin_auth="Authorization: Bearer $ADMIN_TOKEN"
            
            # Test admin endpoints
            result=$(make_curl_request "GET" "/api/admin/users" "" "$admin_auth" "200 404")
            IFS='|' read -r success status_code response <<< "$result"
            print_result "Admin users endpoint" "$success" "Status: $status_code"
            
            result=$(make_curl_request "GET" "/api/admin/system/stats" "" "$admin_auth" "200 404")
            IFS='|' read -r success status_code response <<< "$result"
            print_result "Admin system stats" "$success" "Status: $status_code"
        else
            print_result "Admin login" "false" "No admin token received"
        fi
    else
        print_result "Admin login" "false" "Admin login failed or not available"
    fi
}

# Test database migrations (if alembic is available)
test_database_migrations() {
    print_header "Testing Database Migrations"
    
    if command -v alembic >/dev/null 2>&1; then
        print_result "Alembic availability" "true" "Alembic command found"
        
        # Check current migration status
        if cd backend 2>/dev/null; then
            if alembic current >/dev/null 2>&1; then
                print_result "Database migration status" "true" "Alembic can check migration status"
                
                # Try to run migrations
                if alembic upgrade head >/dev/null 2>&1; then
                    print_result "Database migration execution" "true" "Migrations executed successfully"
                else
                    print_result "Database migration execution" "false" "Migration execution failed"
                fi
            else
                print_result "Database migration status" "false" "Cannot check migration status"
            fi
            cd - >/dev/null
        else
            print_result "Database migration status" "false" "Backend directory not found"
        fi
    else
        print_result "Alembic availability" "false" "Alembic command not found"
    fi
}

# Test external integrations
test_external_integrations() {
    print_header "Testing External Integrations"
    
    # Test ADB availability
    if command -v adb >/dev/null 2>&1; then
        print_result "ADB integration" "true" "ADB command found in PATH"
        
        # Test ADB devices command
        if adb devices >/dev/null 2>&1; then
            print_result "ADB device detection" "true" "ADB devices command works"
        else
            print_result "ADB device detection" "false" "ADB devices command failed"
        fi
    else
        print_result "ADB integration" "false" "ADB not found in PATH"
    fi
    
    # Test network connectivity
    if curl -s --connect-timeout 5 https://httpbin.org/json >/dev/null 2>&1; then
        print_result "External API connectivity" "true" "Network connectivity test successful"
    else
        print_result "External API connectivity" "false" "Network connectivity test failed"
    fi
}

# Print final summary
print_summary() {
    local total=$((PASS_COUNT + FAIL_COUNT))
    
    echo -e "\n${BOLD}Test Summary:${NC}"
    echo "Total: $total"
    echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
    echo -e "${RED}Failed: $FAIL_COUNT${NC}"
    
    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "\n${GREEN}${BOLD}All tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}${BOLD}Some tests failed. Please check the output above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}${BOLD}AndroidZen Pro API Testing with cURL${NC}"
    echo "Testing server at: $BASE_URL"
    echo "Started at: $(date)"
    
    # Wait for server
    if ! wait_for_server; then
        echo -e "${RED}Server not available, exiting.${NC}"
        exit 1
    fi
    
    # Run all tests
    test_public_endpoints
    test_cors
    test_authentication
    test_protected_endpoints
    test_websocket_endpoints
    test_admin_endpoints
    test_file_operations
    test_database_migrations
    test_external_integrations
    
    # Print summary and exit with appropriate code
    echo -e "\n${BLUE}Testing completed at: $(date)${NC}"
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
