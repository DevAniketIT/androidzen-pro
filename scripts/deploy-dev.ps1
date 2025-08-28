# AndroidZen Pro - Development Deployment Script (Windows PowerShell)
# This script sets up and starts the development environment on Windows

param(
    [switch]$Tools,
    [switch]$Help
)

# Colors for output
$ErrorColor = "Red"
$SuccessColor = "Green"
$WarningColor = "Yellow"
$InfoColor = "Blue"

# Functions for colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $InfoColor
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $SuccessColor
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $WarningColor
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ErrorColor
}

# Help message
if ($Help) {
    Write-Host "AndroidZen Pro - Development Deployment Script (Windows)"
    Write-Host "Usage: .\deploy-dev.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Tools     Start optional tools (pgAdmin, Redis Commander)"
    Write-Host "  -Help      Show this help message"
    exit 0
}

# Check if Docker is installed and running
function Test-Docker {
    Write-Status "Checking Docker installation..."
    
    try {
        $dockerVersion = docker --version 2>$null
        if (-not $dockerVersion) {
            Write-Error "Docker is not installed. Please install Docker Desktop first."
            exit 1
        }
        
        $dockerInfo = docker info 2>$null
        if (-not $dockerInfo) {
            Write-Error "Docker is not running. Please start Docker Desktop first."
            exit 1
        }
        
        Write-Success "Docker is installed and running"
    }
    catch {
        Write-Error "Failed to check Docker status: $_"
        exit 1
    }
}

# Check if Docker Compose is available
function Test-DockerCompose {
    Write-Status "Checking Docker Compose..."
    
    try {
        $composeVersion = docker compose version 2>$null
        if ($composeVersion) {
            $global:ComposeCommand = "docker compose"
        } else {
            $composeVersion = docker-compose version 2>$null
            if ($composeVersion) {
                $global:ComposeCommand = "docker-compose"
            } else {
                Write-Error "Docker Compose is not available. Please install Docker Compose."
                exit 1
            }
        }
        
        Write-Success "Docker Compose is available: $global:ComposeCommand"
    }
    catch {
        Write-Error "Failed to check Docker Compose: $_"
        exit 1
    }
}

# Create .env file from .env.example if it doesn't exist
function Initialize-EnvFile {
    Write-Status "Setting up environment file..."
    
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Creating from .env.example..."
        Copy-Item ".env.example" ".env"
        Write-Success ".env file created from .env.example"
        Write-Warning "Please review and update .env file with your specific configuration"
    } else {
        Write-Success ".env file already exists"
    }
}

# Create required directories
function New-RequiredDirectories {
    Write-Status "Creating required directories..."
    
    $directories = @("logs", "uploads", "database\init", "database\backups")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Success "Required directories created"
}

# Build and start services
function Start-Services {
    Write-Status "Building and starting development services..."
    
    try {
        # Pull latest images
        & $global:ComposeCommand.Split() pull
        
        # Build services
        & $global:ComposeCommand.Split() build --no-cache
        
        # Start services
        $profiles = if ($Tools) { "--profile", "tools" } else { @() }
        & $global:ComposeCommand.Split() up -d @profiles
        
        Write-Success "Services started successfully"
    }
    catch {
        Write-Error "Failed to start services: $_"
        exit 1
    }
}

# Wait for services to be healthy
function Wait-ForServices {
    Write-Status "Waiting for services to be healthy..."
    
    # Wait for database
    Write-Status "Waiting for PostgreSQL..."
    $timeout = 60
    $elapsed = 0
    do {
        try {
            $pgReady = & $global:ComposeCommand.Split() exec -T postgres pg_isready -U androidzen_user -d androidzen 2>$null
            if ($LASTEXITCODE -eq 0) { break }
        }
        catch { }
        Start-Sleep 2
        $elapsed += 2
    } while ($elapsed -lt $timeout)
    
    # Wait for Redis
    Write-Status "Waiting for Redis..."
    $timeout = 30
    $elapsed = 0
    do {
        try {
            $redisReady = & $global:ComposeCommand.Split() exec -T redis redis-cli ping 2>$null
            if ($redisReady -eq "PONG") { break }
        }
        catch { }
        Start-Sleep 2
        $elapsed += 2
    } while ($elapsed -lt $timeout)
    
    # Wait for backend
    Write-Status "Waiting for Backend API..."
    $timeout = 90
    $elapsed = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { break }
        }
        catch { }
        Start-Sleep 5
        $elapsed += 5
    } while ($elapsed -lt $timeout)
    
    # Wait for frontend
    Write-Status "Waiting for Frontend..."
    $timeout = 60
    $elapsed = 0
    do {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { break }
        }
        catch { }
        Start-Sleep 5
        $elapsed += 5
    } while ($elapsed -lt $timeout)
    
    Write-Success "All services are healthy"
}

# Display service status
function Show-Status {
    Write-Status "Service Status:"
    & $global:ComposeCommand.Split() ps
    
    Write-Host ""
    Write-Success "Development environment is ready!"
    Write-Host ""
    Write-Status "Access your application:"
    Write-Host "  Frontend:    http://localhost:3000"
    Write-Host "  Backend API: http://localhost:8000"
    Write-Host "  API Docs:    http://localhost:8000/docs"
    Write-Host ""
    
    if ($Tools) {
        Write-Status "Optional services:"
        Write-Host "  pgAdmin:         http://localhost:8080"
        Write-Host "  Redis Commander: http://localhost:8081"
        Write-Host ""
    }
    
    Write-Status "To view logs: $global:ComposeCommand logs -f [service_name]"
    Write-Status "To stop services: $global:ComposeCommand down"
}

# Main execution
function Main {
    Write-Host "======================================================" -ForegroundColor $InfoColor
    Write-Host "AndroidZen Pro - Development Deployment (Windows)" -ForegroundColor $InfoColor
    Write-Host "======================================================" -ForegroundColor $InfoColor
    Write-Host ""
    
    Test-Docker
    Test-DockerCompose
    Initialize-EnvFile
    New-RequiredDirectories
    Start-Services
    Wait-ForServices
    Show-Status
    
    Write-Host ""
    Write-Success "Development environment deployment completed successfully!"
}

# Run main function
try {
    Main
}
catch {
    Write-Error "Deployment failed: $_"
    exit 1
}
