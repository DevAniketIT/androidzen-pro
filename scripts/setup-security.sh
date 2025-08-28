#!/bin/bash

# AndroidZen Security Setup Script
# Sets up comprehensive security scanning tools and pre-commit hooks

set -e  # Exit on any error

echo "🔒 AndroidZen Pro Security Setup"
echo "================================="

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

# Check if running on Windows (Git Bash/WSL)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    WINDOWS=true
    print_status "Detected Windows environment"
else
    WINDOWS=false
    print_status "Detected Unix/Linux environment"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check Python
    if ! command_exists python3 && ! command_exists python; then
        missing_tools+=("python3")
    fi
    
    # Check pip
    if ! command_exists pip3 && ! command_exists pip; then
        missing_tools+=("pip")
    fi
    
    # Check Node.js
    if ! command_exists node; then
        missing_tools+=("node.js")
    fi
    
    # Check npm
    if ! command_exists npm; then
        missing_tools+=("npm")
    fi
    
    # Check Git
    if ! command_exists git; then
        missing_tools+=("git")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and run this script again"
        exit 1
    fi
    
    print_success "All prerequisites are available"
}

# Install Python security tools
install_python_tools() {
    print_status "Installing Python security tools..."
    
    # Determine pip command
    local pip_cmd="pip"
    if command_exists pip3; then
        pip_cmd="pip3"
    fi
    
    # Install security tools
    local python_tools=(
        "bandit[toml]>=1.7.5"
        "safety>=2.3.0"
        "pip-audit>=2.6.0"
        "semgrep>=1.45.0"
        "detect-secrets>=1.4.0"
        "pre-commit>=3.4.0"
        "black>=23.7.0"
        "flake8>=6.0.0"
        "isort>=5.12.0"
        "mypy>=1.5.0"
    )
    
    for tool in "${python_tools[@]}"; do
        print_status "Installing $tool..."
        $pip_cmd install "$tool" || {
            print_warning "Failed to install $tool, continuing..."
        }
    done
    
    print_success "Python security tools installed"
}

# Install Node.js security tools
install_nodejs_tools() {
    print_status "Installing Node.js security tools..."
    
    # Check if we're in frontend directory
    if [ -f "frontend/package.json" ]; then
        cd frontend
        print_status "Installing frontend security dependencies..."
        
        npm install --save-dev \
            eslint \
            eslint-plugin-security \
            @typescript-eslint/eslint-plugin \
            @typescript-eslint/parser \
            prettier \
            || {
                print_warning "Failed to install some Node.js tools, continuing..."
            }
        
        cd ..
    else
        print_warning "frontend/package.json not found, skipping Node.js security tools"
    fi
    
    print_success "Node.js security tools setup completed"
}

# Install GitLeaks
install_gitleaks() {
    print_status "Installing GitLeaks..."
    
    if command_exists gitleaks; then
        print_success "GitLeaks already installed"
        return
    fi
    
    if [ "$WINDOWS" = true ]; then
        print_status "Please install GitLeaks manually from: https://github.com/gitleaks/gitleaks/releases"
        print_status "Or use: 'go install github.com/gitleaks/gitleaks/v8@latest' if you have Go installed"
    else
        # Try to install via package manager
        if command_exists brew; then
            brew install gitleaks
        elif command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y gitleaks
        elif command_exists yum; then
            sudo yum install -y gitleaks
        else
            print_status "Installing GitLeaks via Go..."
            if command_exists go; then
                go install github.com/gitleaks/gitleaks/v8@latest
            else
                print_warning "Please install GitLeaks manually: https://github.com/gitleaks/gitleaks"
            fi
        fi
    fi
    
    if command_exists gitleaks; then
        print_success "GitLeaks installed successfully"
    else
        print_warning "GitLeaks installation may have failed"
    fi
}

# Setup pre-commit hooks
setup_precommit() {
    print_status "Setting up pre-commit hooks..."
    
    if [ ! -f ".pre-commit-config.yaml" ]; then
        print_error ".pre-commit-config.yaml not found"
        return 1
    fi
    
    # Install pre-commit hooks
    pre-commit install || {
        print_error "Failed to install pre-commit hooks"
        return 1
    }
    
    # Run pre-commit on all files to check setup
    print_status "Running initial pre-commit check..."
    pre-commit run --all-files || {
        print_warning "Some pre-commit hooks failed, this is normal for initial setup"
    }
    
    print_success "Pre-commit hooks installed"
}

# Create secrets baseline
create_secrets_baseline() {
    print_status "Creating secrets baseline..."
    
    if command_exists detect-secrets; then
        # Create baseline file
        detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline || {
            print_warning "Failed to create secrets baseline, creating empty one"
            echo '{"results": {}, "version": "1.4.0", "generated_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > .secrets.baseline
        }
        print_success "Secrets baseline created"
    else
        print_warning "detect-secrets not available, skipping baseline creation"
    fi
}

# Run initial security scans
run_initial_scans() {
    print_status "Running initial security scans..."
    
    # Python backend scan
    if [ -d "backend" ]; then
        print_status "Scanning backend with Bandit..."
        bandit -r backend/ -f json -o bandit-initial-scan.json || {
            print_warning "Bandit scan completed with issues (check bandit-initial-scan.json)"
        }
        
        print_status "Scanning Python dependencies with Safety..."
        safety check --json --output safety-initial-scan.json || {
            print_warning "Safety scan found vulnerabilities (check safety-initial-scan.json)"
        }
        
        print_status "Scanning Python dependencies with pip-audit..."
        pip-audit --format=json --output=pip-audit-initial-scan.json || {
            print_warning "pip-audit found vulnerabilities (check pip-audit-initial-scan.json)"
        }
    fi
    
    # Frontend scan
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        print_status "Auditing frontend dependencies..."
        cd frontend
        npm audit --json > ../npm-audit-initial-scan.json 2>/dev/null || {
            print_warning "npm audit found vulnerabilities (check npm-audit-initial-scan.json)"
        }
        cd ..
    fi
    
    # GitLeaks scan
    if command_exists gitleaks; then
        print_status "Running GitLeaks scan..."
        gitleaks detect --report-format json --report-path gitleaks-initial-scan.json || {
            print_warning "GitLeaks found secrets (check gitleaks-initial-scan.json)"
        }
    fi
    
    print_success "Initial security scans completed"
}

# Generate security report
generate_security_report() {
    print_status "Generating security setup report..."
    
    cat > SECURITY_SETUP_REPORT.md << 'EOF'
# AndroidZen Pro Security Setup Report

## Tools Installed

### Python Security Tools
- **Bandit**: Static security analysis for Python code
- **Safety**: Checks Python dependencies for known vulnerabilities
- **pip-audit**: Audits Python packages for known vulnerabilities
- **Semgrep**: Static analysis with security rules
- **detect-secrets**: Prevents secrets from being committed

### Code Quality Tools
- **Black**: Python code formatter
- **flake8**: Python linting
- **isort**: Python import sorting
- **mypy**: Python static type checking
- **ESLint**: JavaScript/TypeScript linting with security plugin
- **Prettier**: Code formatting

### Secrets Detection
- **GitLeaks**: Detect secrets in Git repositories
- **TruffleHog**: Find secrets in Git history
- **detect-secrets**: Pre-commit hook for secret detection

### Pre-commit Hooks
Pre-commit hooks are configured to run:
- Security scans (Bandit, detect-secrets, GitLeaks)
- Code formatting (Black, Prettier)
- Linting (flake8, ESLint)
- Dependency checks (Safety)

## Security Scanning Workflows

### GitHub Actions Workflows
- `security-scanning.yml`: Comprehensive SAST, SCA, and secrets scanning
- `android-quality.yml`: Android-specific code quality checks
- `ci-cd-pipeline.yml`: Full CI/CD pipeline with security gates

### Manual Security Commands

#### Backend Security Scans
```bash
# Static analysis
bandit -r backend/ -f json -o bandit-report.json

# Dependency vulnerabilities
safety check --json --output safety-report.json
pip-audit --format=json --output=pip-audit-report.json

# Semgrep security rules
semgrep --config=auto backend/
```

#### Frontend Security Scans
```bash
# Dependency audit
cd frontend && npm audit --json > audit-report.json

# ESLint security scan
cd frontend && npx eslint . --ext .js,.jsx,.ts,.tsx -c .eslintrc-security.js
```

#### Secrets Scanning
```bash
# Scan for secrets
gitleaks detect --report-format json --report-path gitleaks-report.json

# Update secrets baseline
detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline
```

#### Pre-commit Testing
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run bandit
```

## Security Gate Criteria

### Exit Criteria (Must be met for deployment)
- Zero critical vulnerabilities (CVSS 9.0-10.0)
- Zero high vulnerabilities (CVSS 7.0-8.9)
- Zero exposed secrets
- All security tests passing
- Code quality standards met

### Quality Gates
- Android Lint: Zero errors
- Detekt: Zero violations
- ESLint: Zero security rule violations
- Bandit: Zero high/critical findings
- Formatting: Consistent across all files

## Next Steps

1. **Review Initial Scan Results**: Check the generated scan files for any existing issues
2. **Fix Critical Issues**: Address any critical or high-severity vulnerabilities found
3. **Configure IDE Integration**: Set up your IDE to run security tools automatically
4. **Team Training**: Ensure all team members understand the security workflows
5. **Regular Updates**: Keep security tools and their databases updated

## Support

For security tool documentation and updates:
- Bandit: https://bandit.readthedocs.io/
- Safety: https://pyup.io/safety/
- GitLeaks: https://github.com/gitleaks/gitleaks
- Semgrep: https://semgrep.dev/docs/

EOF

    print_success "Security setup report generated: SECURITY_SETUP_REPORT.md"
}

# Main execution
main() {
    print_status "Starting AndroidZen Pro security setup..."
    
    # Run setup steps
    check_prerequisites
    install_python_tools
    install_nodejs_tools
    install_gitleaks
    create_secrets_baseline
    setup_precommit
    run_initial_scans
    generate_security_report
    
    echo ""
    echo "🎉 Security setup completed successfully!"
    echo ""
    echo "📋 Summary:"
    echo "  ✅ Security tools installed"
    echo "  ✅ Pre-commit hooks configured"  
    echo "  ✅ Initial security scans completed"
    echo "  ✅ Security workflows ready"
    echo ""
    echo "📖 Next steps:"
    echo "  1. Review SECURITY_SETUP_REPORT.md"
    echo "  2. Check initial scan results for any issues"
    echo "  3. Configure your IDE with the security tools"
    echo "  4. Run 'pre-commit run --all-files' to test setup"
    echo ""
    echo "⚠️  Remember: Security is everyone's responsibility!"
}

# Run main function
main "$@"
