# Contributing to AndroidZen Pro

Thank you for your interest in contributing to AndroidZen Pro! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)
- [Community Guidelines](#community-guidelines)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

### Our Pledge

We pledge to make participation in our project and community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Harassment, trolling, insulting/derogatory comments
- Public or private harassment
- Publishing others' private information without permission
- Any conduct that could reasonably be considered inappropriate

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Development Environment**: See [INSTALLATION.md](INSTALLATION.md)
2. **Git Setup**: Configure Git with your name and email
3. **GitHub Account**: For submitting pull requests
4. **Project Knowledge**: Read the README and API documentation

### First-Time Setup

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/androidzen-pro.git
cd androidzen-pro

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/androidzen-pro.git

# Install development dependencies
pip install -r requirements.txt
npm install --prefix frontend

# Install pre-commit hooks
pre-commit install

# Set up development environment
cp .env.example .env
docker compose up -d
```

### Development Environment

We use:
- **Pre-commit hooks**: Code formatting and linting
- **Docker**: Consistent development environment
- **GitHub Actions**: Automated testing and deployment
- **Code coverage**: Maintain minimum 80% coverage

## Development Workflow

### Branch Strategy

We follow a modified Git Flow:

- `main`: Production-ready code
- `develop`: Development integration branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Critical production fixes
- `release/*`: Release preparation

### Creating a Feature

```bash
# Start from develop
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature description"

# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**
```bash
feat(auth): add OAuth2 authentication
fix(devices): resolve device connection timeout
docs(api): update endpoint documentation
test(storage): add unit tests for storage service
```

### Branch Naming

- `feature/issue-123-add-device-monitoring`
- `bugfix/fix-websocket-connection`
- `hotfix/security-vulnerability-patch`
- `docs/update-installation-guide`

## Coding Standards

### Python (Backend)

**Style Guide:** Follow PEP 8 with these extensions:

```python
# Import organization
import os
import sys
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import User

# Function annotations
def get_user_devices(
    user_id: str, 
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all devices for a user."""
    pass

# Class definitions
class DeviceService:
    """Service for managing device operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_device(self, device_data: Dict[str, Any]) -> Device:
        """Create a new device."""
        pass
```

**Key Requirements:**
- Use type hints for all functions and methods
- Include docstrings for all public functions
- Maximum line length: 88 characters (Black formatter)
- Use f-strings for string formatting
- Prefer explicit imports over wildcard imports

**Tools:**
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security linting

### TypeScript/React (Frontend)

**Style Guide:** Follow Airbnb TypeScript style guide

```typescript
// Interface definitions
interface Device {
  id: string;
  name: string;
  isConnected: boolean;
  batteryLevel?: number;
}

// Component definitions
interface DeviceCardProps {
  device: Device;
  onUpdate: (device: Device) => void;
}

const DeviceCard: React.FC<DeviceCardProps> = ({ device, onUpdate }) => {
  const handleClick = useCallback(() => {
    onUpdate(device);
  }, [device, onUpdate]);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">{device.name}</Typography>
        <Typography color="textSecondary">
          Status: {device.isConnected ? 'Connected' : 'Disconnected'}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default DeviceCard;
```

**Key Requirements:**
- Use TypeScript interfaces for all data structures
- Prefer functional components with hooks
- Use meaningful component and variable names
- Include JSDoc comments for complex functions
- Use ESLint and Prettier configurations

**Tools:**
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **TypeScript**: Type checking
- **Jest**: Testing framework

### Database

**Migrations:**
- Always create migrations for schema changes
- Include both upgrade and downgrade operations
- Test migrations on sample data
- Use descriptive migration names

```python
"""Add device monitoring table

Revision ID: 12345abcdef
Revises: 98765fedcba
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'device_monitoring',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
    )

def downgrade():
    op.drop_table('device_monitoring')
```

### API Design

**RESTful Principles:**
- Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- Return appropriate status codes
- Include comprehensive error messages
- Use consistent response formats

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

class DeviceResponse(BaseModel):
    id: str
    name: str
    is_connected: bool

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str) -> DeviceResponse:
    """Get device by ID."""
    device = await device_service.get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return DeviceResponse(**device.dict())
```

## Testing Guidelines

### Backend Testing

**Test Structure:**
```python
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import get_db
from tests.fixtures import test_user, test_device

client = TestClient(app)

class TestDeviceAPI:
    """Test device API endpoints."""
    
    def test_get_devices_authenticated(self, test_user):
        """Test getting devices with authentication."""
        token = self.get_auth_token(test_user)
        response = client.get(
            "/api/devices/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "devices" in response.json()
    
    def test_get_devices_unauthenticated(self):
        """Test getting devices without authentication."""
        response = client.get("/api/devices/")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_device_service_create_device(self, test_db):
        """Test device service create device method."""
        device_data = {
            "name": "Test Device",
            "model": "Test Model"
        }
        device = await device_service.create_device(test_db, device_data)
        assert device.name == "Test Device"
```

**Testing Requirements:**
- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test API endpoints and database operations
- **Coverage**: Minimum 80% code coverage
- **Fixtures**: Use pytest fixtures for test data
- **Mocking**: Mock external services and dependencies

**Running Tests:**
```bash
# Backend tests
pytest backend/tests/ -v --cov=backend --cov-report=html

# Frontend tests
cd frontend && npm test -- --coverage --watchAll=false

# End-to-end tests
pytest tests/e2e/ -v
```

### Frontend Testing

**Test Structure:**
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

import DeviceCard from './DeviceCard';
import { Device } from '../types';

const mockDevice: Device = {
  id: '123',
  name: 'Test Device',
  isConnected: true,
  batteryLevel: 85,
};

const server = setupServer(
  rest.get('/api/devices/123', (req, res, ctx) => {
    return res(ctx.json(mockDevice));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('DeviceCard', () => {
  it('renders device information', () => {
    render(<DeviceCard device={mockDevice} onUpdate={jest.fn()} />);
    
    expect(screen.getByText('Test Device')).toBeInTheDocument();
    expect(screen.getByText('Status: Connected')).toBeInTheDocument();
  });

  it('calls onUpdate when clicked', () => {
    const mockOnUpdate = jest.fn();
    render(<DeviceCard device={mockDevice} onUpdate={mockOnUpdate} />);
    
    fireEvent.click(screen.getByRole('button'));
    
    expect(mockOnUpdate).toHaveBeenCalledWith(mockDevice);
  });
});
```

**Testing Tools:**
- **Jest**: Test runner and assertion library
- **React Testing Library**: Component testing utilities
- **MSW**: API mocking
- **Cypress**: End-to-end testing (optional)

### Testing Best Practices

1. **Write tests before fixing bugs**: Reproduce the bug with a test
2. **Test edge cases**: Handle empty data, errors, and boundary conditions
3. **Use descriptive test names**: Clearly describe what is being tested
4. **Keep tests independent**: Each test should run in isolation
5. **Mock external dependencies**: Database, APIs, file systems

## Documentation

### Code Documentation

**Python Docstrings:**
```python
def calculate_storage_usage(device_id: str, category: str = None) -> Dict[str, float]:
    """Calculate storage usage for a device.
    
    Args:
        device_id: Unique identifier for the device
        category: Optional category filter (apps, photos, videos, etc.)
        
    Returns:
        Dictionary containing storage usage statistics
        
    Raises:
        DeviceNotFoundError: If device_id is not found
        StorageAccessError: If storage data cannot be accessed
        
    Example:
        >>> usage = calculate_storage_usage("device_123", "apps")
        >>> print(usage["total_gb"])
        15.4
    """
    pass
```

**TypeScript JSDoc:**
```typescript
/**
 * Connects to device via WebSocket and monitors real-time updates
 * @param deviceId - Unique device identifier  
 * @param onUpdate - Callback function for device updates
 * @returns Promise that resolves to WebSocket connection
 * @throws {ConnectionError} When WebSocket connection fails
 * @example
 * ```typescript
 * const connection = await connectToDevice('device_123', (data) => {
 *   console.log('Device update:', data);
 * });
 * ```
 */
async function connectToDevice(
  deviceId: string,
  onUpdate: (data: DeviceUpdate) => void
): Promise<WebSocket> {
  // Implementation
}
```

### API Documentation

- Keep API.md updated with new endpoints
- Include request/response examples
- Document error responses and status codes
- Update OpenAPI schema in code

### README Updates

When adding features:
- Update feature list in README.md
- Add installation notes if needed
- Update configuration examples
- Include usage examples

## Submitting Changes

### Pull Request Process

1. **Preparation:**
   ```bash
   # Update your fork
   git checkout develop
   git pull upstream develop
   
   # Rebase your feature branch
   git checkout feature/your-feature
   git rebase develop
   
   # Run tests and linting
   pre-commit run --all-files
   pytest
   npm test --prefix frontend
   ```

2. **Create Pull Request:**
   - Use the PR template
   - Include clear title and description
   - Reference related issues
   - Add screenshots for UI changes
   - Ensure CI checks pass

3. **PR Template:**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Tests pass
   - [ ] New tests added
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No breaking changes or clearly documented
   ```

### Code Review Checklist

**For Reviewers:**
- [ ] Code follows project conventions
- [ ] Tests are comprehensive and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Breaking changes documented

**For Authors:**
- [ ] PR description is clear and complete
- [ ] All CI checks pass
- [ ] Code is self-documenting
- [ ] Tests cover new functionality
- [ ] Documentation updated

## Review Process

### Review Timeline

- **Initial Response**: Within 2 business days
- **Full Review**: Within 5 business days
- **Follow-up**: Within 1 business day

### Review Criteria

**Code Quality:**
- Follows coding standards
- Includes appropriate tests
- Has clear documentation
- No obvious security issues

**Functionality:**
- Solves the intended problem
- Doesn't break existing features
- Includes error handling
- Considers edge cases

**Design:**
- Follows project architecture
- Uses appropriate patterns
- Considers maintainability
- Has reasonable performance

### Addressing Feedback

```bash
# Address review feedback
git checkout feature/your-feature

# Make changes
# ... edit files ...

# Commit changes
git add .
git commit -m "fix: address review feedback"

# Push updates
git push origin feature/your-feature
```

## Community Guidelines

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and discussion

### Issue Guidelines

**Bug Reports:**
```markdown
**Describe the bug**
A clear and concise description

**To Reproduce**
1. Steps to reproduce
2. Expected behavior
3. Actual behavior

**Environment**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.11]
- Docker version: [e.g., 20.10]

**Additional context**
Screenshots, logs, etc.
```

**Feature Requests:**
```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution**
Clear description of desired feature

**Additional context**
Mockups, examples, alternatives considered
```

### Getting Help

1. **Search existing issues** before creating new ones
2. **Use clear, descriptive titles** for issues and PRs
3. **Provide context** and examples
4. **Be patient and respectful** in discussions
5. **Tag maintainers** only when necessary

### Recognition

Contributors are recognized through:
- **Contributors list** in README.md
- **Release notes** mentioning significant contributions
- **GitHub contributor graph** and statistics
- **Community appreciation** in discussions

## Development Tips

### Local Development

```bash
# Quick development server restart
docker compose restart backend frontend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Run specific tests
pytest backend/tests/test_auth.py::test_login -v

# Database operations
docker compose exec backend alembic upgrade head
docker compose exec postgres psql -U androidzen_user androidzen
```

### Debugging

```python
# Backend debugging
import pdb; pdb.set_trace()  # Python debugger
logger.debug(f"Processing device: {device_id}")  # Logging

# Use environment variables for debugging
DEBUG=True uvicorn backend.main:app --reload
```

```typescript
// Frontend debugging
console.log('Device data:', device);
debugger; // Browser debugger

// React Developer Tools
// Use browser extension for component inspection
```

### Performance Considerations

- **Database**: Use indexes, optimize queries
- **API**: Implement pagination, caching
- **Frontend**: Lazy loading, code splitting
- **Docker**: Multi-stage builds, layer optimization

Thank you for contributing to AndroidZen Pro! Your contributions help make this project better for everyone.
