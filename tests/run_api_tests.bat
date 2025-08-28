@echo off
REM AndroidZen Pro API Testing - Windows Batch Script
REM This script runs the comprehensive API and integration tests

echo.
echo ========================================
echo AndroidZen Pro API Testing Suite
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Python is available
echo.

REM Check if the server is running
echo Checking if server is running...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Server not responding at http://localhost:8000
    echo Please make sure AndroidZen Pro backend is running
    echo.
    set /p choice="Continue anyway? (y/N): "
    if /i not "%choice%"=="y" (
        echo Exiting...
        pause
        exit /b 1
    )
)

echo Server is responding
echo.

REM Install required packages if needed
echo Checking Python dependencies...
python -c "import requests, websockets, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required Python packages...
    pip install requests websockets psutil psycopg2-binary redis
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Python packages
        echo Please install manually: pip install requests websockets psutil
        pause
        exit /b 1
    )
)

echo Dependencies are available
echo.

REM Show menu options
echo Select test type:
echo 1. Full API Integration Test Suite (Recommended)
echo 2. WebSocket Tests Only
echo 3. Run All Tests
echo 4. Exit
echo.

set /p option="Enter your choice (1-4): "

if "%option%"=="1" (
    echo.
    echo Running Full API Integration Test Suite...
    echo ========================================
    python test_api_integration.py
    goto :end
)

if "%option%"=="2" (
    echo.
    echo Running WebSocket Tests...
    echo ===========================
    python test_websocket.py
    goto :end
)

if "%option%"=="3" (
    echo.
    echo Running All Tests...
    echo ====================
    echo.
    echo 1. API Integration Tests:
    python test_api_integration.py
    echo.
    echo 2. WebSocket Tests:
    python test_websocket.py
    goto :end
)

if "%option%"=="4" (
    echo Exiting...
    goto :end
)

echo Invalid option selected
goto :end

:end
echo.
echo ========================================
echo Testing completed
echo ========================================
echo.

REM Check if results file exists
if exist "api_integration_test_results.json" (
    echo Test results saved to: api_integration_test_results.json
    echo.
)

echo Press any key to exit...
pause >nul
