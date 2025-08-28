# 🤝 Contributing to AndroidZen Pro

Thank you for your interest in contributing to **AndroidZen Pro**! We welcome contributions from the community and are grateful for every contribution, no matter how small.

## 📋 Table of Contents

- [🎯 How to Contribute](#-how-to-contribute)
- [🐛 Reporting Bugs](#-reporting-bugs)  
- [✨ Suggesting Enhancements](#-suggesting-enhancements)
- [💻 Development Setup](#-development-setup)
- [📝 Coding Standards](#-coding-standards)
- [🧪 Testing Guidelines](#-testing-guidelines)
- [📖 Documentation](#-documentation)
- [🔄 Pull Request Process](#-pull-request-process)

---

## 🎯 How to Contribute

There are many ways to contribute to AndroidZen Pro:

### 🚀 **Code Contributions**
- Fix bugs and implement new features
- Improve performance and security
- Add tests and improve code coverage
- Refactor and optimize existing code

### 📚 **Documentation**
- Improve README and documentation
- Write tutorials and guides  
- Translate documentation
- Create video tutorials

### 🐛 **Quality Assurance**
- Report bugs and issues
- Test new features and releases
- Improve test coverage
- Security testing and audits

### 💬 **Community Support**
- Help answer questions in discussions
- Review pull requests
- Mentor new contributors
- Share the project with others

---

## 🐛 Reporting Bugs

Before submitting a bug report:

1. **Search existing issues** to avoid duplicates
2. **Use the latest version** to verify the bug exists
3. **Gather information** about your environment

### 📝 Bug Report Template

```markdown
**Describe the Bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'  
3. See error

**Expected Behavior**
What you expected to happen.

**Screenshots**
Add screenshots if applicable.

**Environment:**
- OS: [e.g. Ubuntu 20.04]
- Browser: [e.g. Chrome 91]
- Version: [e.g. 1.0.0]

**Additional Context**
Any other context about the problem.
```

---

## ✨ Suggesting Enhancements

We love feature suggestions! Before submitting:

1. **Check existing feature requests**
2. **Consider the scope** - does it fit the project goals?
3. **Provide detailed rationale** and use cases

### 💡 Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Screenshots, mockups, or other context.

**Implementation ideas**
If you have thoughts on how to implement this.
```

---

## 💻 Development Setup

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+ and **Node.js** 18+
- **Git** for version control

### 🛠️ Local Development

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/androidzen-pro.git
cd androidzen-pro

# 2. Set up development environment
cp .env.example .env.development

# 3. Start with Docker Compose
docker compose -f docker-compose.dev.yml up -d

# 4. Install dependencies (for local development)
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Frontend  
cd frontend
npm install
```

### 🗄️ Database Setup

```bash
# Run database migrations
cd backend
alembic upgrade head

# Seed development data (optional)
python scripts/seed_data.py
```

---

## 📝 Coding Standards

### 🐍 **Python (Backend)**

We follow **PEP 8** with these extensions:

```python
# Use type hints
def process_device(device_id: str) -> DeviceInfo:
    pass

# Use docstrings for all public functions
def create_user(email: str, password: str) -> User:
    """Create a new user account.
    
    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        
    Returns:
        User object with generated ID
        
    Raises:
        ValidationError: If email is invalid
    """
    pass

# Use dataclasses for data structures
@dataclass
class DeviceConfig:
    device_id: str
    enabled: bool = True
    max_connections: int = 100
```

### ⚛️ **TypeScript/React (Frontend)**

```typescript
// Use functional components with hooks
interface DeviceCardProps {
  device: Device;
  onConnect: (deviceId: string) => void;
}

const DeviceCard: React.FC<DeviceCardProps> = ({ device, onConnect }) => {
  const [isConnecting, setIsConnecting] = useState(false);
  
  return (
    <Card>
      {/* Component JSX */}
    </Card>
  );
};

// Use proper TypeScript types
type DeviceStatus = 'connected' | 'disconnected' | 'error';

interface Device {
  id: string;
  name: string;
  status: DeviceStatus;
  lastSeen: Date;
}
```

### 🔧 **General Guidelines**

- **Meaningful names** for variables and functions
- **Small, focused functions** (< 50 lines)
- **Consistent formatting** using prettier/black
- **Comment complex logic** and business rules
- **No magic numbers** - use constants

---

## 🧪 Testing Guidelines

### 🐍 **Backend Testing**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_device_management.py

# Run with debugging
pytest -s -vv tests/test_api.py::test_create_user
```

### ⚛️ **Frontend Testing**

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test
npm test -- --testNamePattern="Device"

# Run E2E tests
npm run test:e2e
```

### ✅ **Test Requirements**

- **Unit tests** for all new functions
- **Integration tests** for API endpoints
- **Component tests** for React components
- **E2E tests** for critical user flows
- **Minimum 80% code coverage**

---

## 📖 Documentation

### 📚 **Types of Documentation**

- **Code comments** for complex logic
- **API documentation** using OpenAPI/Swagger
- **README updates** for new features
- **Architecture docs** for system changes

### 📝 **Documentation Standards**

```python
# Good: Clear, concise, explains why
def calculate_device_score(metrics: DeviceMetrics) -> float:
    """Calculate device health score based on performance metrics.
    
    The score is calculated using a weighted average of CPU, memory,
    and battery metrics, with higher weights for more critical metrics.
    
    Returns:
        Score between 0.0 (poor) and 1.0 (excellent)
    """
    pass

# Bad: Restates what the code does
def calculate_device_score(metrics: DeviceMetrics) -> float:
    """Calculates device score from metrics."""
    pass
```

---

## 🔄 Pull Request Process

### 📋 **Before Submitting**

1. ✅ **Run all tests** and ensure they pass
2. ✅ **Run linting** and fix any issues  
3. ✅ **Update documentation** if needed
4. ✅ **Add/update tests** for your changes
5. ✅ **Squash commits** into logical units

### 📝 **PR Description Template**

```markdown
## 📋 Description
Brief description of changes.

## 🎯 Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Breaking change
- [ ] Documentation update

## 🧪 Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## 📸 Screenshots (if applicable)

## 🔗 Related Issues
Closes #123
```

### 🔍 **Review Process**

1. **Automated checks** must pass (CI/CD)
2. **Two approvals** from maintainers required
3. **Address feedback** promptly and professionally  
4. **Final review** by project lead for significant changes

---

## 🏷️ **Git Commit Guidelines**

We use **Conventional Commits** format:

```bash
# Format: type(scope): description

# Examples:
feat(auth): add OAuth2 integration
fix(api): resolve device connection timeout  
docs(readme): update installation instructions
test(device): add unit tests for device manager
refactor(ui): simplify device card component
```

### **Commit Types**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

---

## 🏅 **Recognition**

Contributors will be recognized in:

- **README.md** contributors section
- **Release notes** for significant contributions
- **Annual contributor spotlight**
- **Conference speaking opportunities**

---

## 📞 **Need Help?**

- 💬 **Discussions**: [GitHub Discussions](https://github.com/DevAniketIT/androidzen-pro/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/DevAniketIT/androidzen-pro/issues)
- 📧 **Email**: contribute@androidzen.pro
- 💬 **Discord**: [Join our community](https://discord.gg/androidzen)

---

## 📜 **Code of Conduct**

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). 

**In summary:**
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different opinions and approaches

---

**Thank you for contributing to AndroidZen Pro! 🚀**

> "Great software is built by great communities. Every contribution matters."
