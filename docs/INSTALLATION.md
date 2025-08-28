# Installation Guide

This guide provides detailed setup instructions for AndroidZen Pro in both development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Manual Development Setup](#manual-development-setup)
- [Production Setup](#production-setup)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB free space
- OS: Linux, macOS, or Windows with WSL2

**Recommended:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 20GB+ free space

### Required Software

**For Docker Setup (Recommended):**
- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

**For Manual Setup:**
- [Python](https://www.python.org/downloads/) 3.11+
- [Node.js](https://nodejs.org/) 18+
- [Git](https://git-scm.com/)
- [PostgreSQL](https://www.postgresql.org/download/) 15+ (optional, can use SQLite for development)
- [Redis](https://redis.io/download) 7+ (optional for development)

### Verification

```bash
# Check Docker
docker --version
docker compose version

# Check Python
python3 --version
pip --version

# Check Node.js
node --version
npm --version

# Check Git
git --version
```

## Quick Start (Docker)

The fastest way to get AndroidZen Pro running:

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_GITHUB_ORG/androidzen-pro.git
cd androidzen-pro
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional for development)
# The defaults work fine for local development
```

### 3. Start Services

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Access Applications

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **pgAdmin** (optional): http://localhost:8080 (admin@androidzen.local / admin123)
- **Redis Commander** (optional): http://localhost:8081

### 5. Default Credentials

- **Admin User**: admin / admin123
- **Demo User**: demo / demo123

### 6. Optional Tools

Start with additional development tools:

```bash
# Start with pgAdmin and Redis Commander
docker compose --profile tools up -d
```

## Manual Development Setup

For development without Docker:

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_GITHUB_ORG/androidzen-pro.git
cd androidzen-pro
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite:///database/androidzen.db"
export SECRET_KEY="your-secret-key-here"

# Create directories
mkdir -p database logs uploads

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Set environment variables
export REACT_APP_API_URL="http://localhost:8000"
export REACT_APP_WS_URL="ws://localhost:8000/ws"

# Start development server
npm start
```

### 4. Database Setup (Optional PostgreSQL)

```bash
# Create database (if using PostgreSQL)
createdb androidzen

# Update DATABASE_URL in .env
DATABASE_URL="postgresql://username:password@localhost:5432/androidzen"
```

### 5. Redis Setup (Optional)

```bash
# Start Redis server
redis-server

# Update REDIS_URL in .env
REDIS_URL="redis://localhost:6379/0"
```

## Production Setup

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive instructions. Key points:

### 1. Environment Variables

Create production `.env` file:

```env
# Security
DEBUG=False
SECRET_KEY=your-very-secure-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_URL=postgresql://user:password@db-host:5432/androidzen

# Redis
REDIS_URL=redis://redis-host:6379/0

# URLs
BACKEND_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# SSL
SSL_REDIRECT=True
```

### 2. Production Deployment

```bash
# Build and deploy
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create superuser
docker compose -f docker-compose.prod.yml exec backend python -c "
from backend.core.database import get_db
from backend.models.user import User
from backend.core.auth import auth_manager
db = next(get_db())
User.create_user(db, {
    'username': 'admin',
    'email': 'admin@yourdomain.com',
    'hashed_password': auth_manager.get_password_hash('secure-password'),
    'is_admin': True
})
"
```

## Configuration

### Environment Variables

Key environment variables:

```env
# Application
DEBUG=True                    # Enable debug mode
SECRET_KEY=secret            # Application secret
JWT_SECRET_KEY=jwt-secret    # JWT signing key
ENVIRONMENT=development      # Environment name

# Database
DATABASE_URL=sqlite:///database/androidzen.db  # Database connection

# Redis
REDIS_URL=redis://localhost:6379/0  # Redis connection

# Logging
LOG_LEVEL=INFO              # Logging level
LOG_FORMAT=console          # Log format (console/json)

# Security
CORS_ORIGINS=http://localhost:3000  # Allowed CORS origins
RATE_LIMIT_ENABLED=True     # Enable rate limiting

# Features
ENABLE_AI_FEATURES=True     # Enable AI analytics
ENABLE_WEBSOCKET=True       # Enable WebSocket support
```

### Feature Flags

Enable/disable features:

```env
# AI Features
ENABLE_AI_ANALYTICS=True
ENABLE_PREDICTIVE_MAINTENANCE=True
ENABLE_ANOMALY_DETECTION=True

# Monitoring
ENABLE_PERFORMANCE_MONITORING=True
ENABLE_ERROR_TRACKING=True
ENABLE_SECURITY_LOGGING=True

# Integrations
ENABLE_NOTIFICATIONS=True
ENABLE_BACKUP_SCHEDULING=True
```

## Database Setup

### SQLite (Development)

```bash
# Automatic setup with migrations
mkdir -p database
alembic upgrade head
```

### PostgreSQL (Production)

```bash
# Create database
sudo -u postgres createdb androidzen
sudo -u postgres createuser androidzen_user
sudo -u postgres psql -c "ALTER USER androidzen_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE androidzen TO androidzen_user;"

# Update DATABASE_URL
DATABASE_URL="postgresql://androidzen_user:secure_password@localhost:5432/androidzen"

# Run migrations
alembic upgrade head
```

### Database Initialization

```bash
# Create default users and data
python -c "
from backend.core.database import get_db
from backend.models.user import User
from backend.core.auth import auth_manager

db = next(get_db())

# Create admin user
admin_data = {
    'username': 'admin',
    'email': 'admin@androidzen.local',
    'hashed_password': auth_manager.get_password_hash('admin123'),
    'is_admin': True,
    'full_name': 'Administrator'
}
User.create_user(db, admin_data)

# Create demo user
demo_data = {
    'username': 'demo',
    'email': 'demo@androidzen.local',
    'hashed_password': auth_manager.get_password_hash('demo123'),
    'full_name': 'Demo User'
}
User.create_user(db, demo_data)

print('Default users created successfully')
"
```

## Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :3000

# Kill process
sudo kill -9 <PID>
```

**2. Permission Denied (Docker)**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

**3. Database Connection Error**
```bash
# Check database status
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Reset database
docker compose down -v
docker compose up -d postgres
```

**4. Frontend Build Errors**
```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**5. Module Not Found Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Health Checks

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Check WebSocket
curl -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws

# Check database connectivity
docker compose exec postgres pg_isready

# Check Redis
docker compose exec redis redis-cli ping
```

### Logs

```bash
# View all logs
docker compose logs

# View specific service logs
docker compose logs backend
docker compose logs frontend
docker compose logs postgres

# Follow logs
docker compose logs -f backend

# View application logs (manual setup)
tail -f logs/androidzen-pro.log
```

### Performance Optimization

**Development:**
```bash
# Increase Docker memory
# Docker Desktop: Settings > Resources > Memory > 6GB+

# Use faster file watching (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**Production:**
```bash
# Optimize database
# Edit postgresql.conf:
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB

# Optimize Redis
# Edit redis.conf:
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### Getting Help

1. Check the [Issues](https://github.com/YOUR_GITHUB_ORG/androidzen-pro/issues) page
2. Review [API Documentation](API.md)
3. Check [Deployment Guide](DEPLOYMENT.md)
4. Contact the development team

### Verification

After installation, verify the setup:

```bash
# Run health checks
curl http://localhost:8000/health
curl http://localhost:3000

# Run tests
docker compose exec backend python -m pytest
docker compose exec frontend npm test

# Check API endpoints
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/devices/
```

## Next Steps

1. Read the [API Documentation](API.md)
2. Review [Contributing Guidelines](CONTRIBUTING.md)
3. Check [Security Policies](SECURITY.md)
4. Set up [Production Deployment](DEPLOYMENT.md)

For additional help, see the project's GitHub Issues or contact the development team.
