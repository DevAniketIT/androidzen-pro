# AndroidZen Pro - Deployment Guide

This guide covers the deployment configurations and scripts for AndroidZen Pro, including both development and production environments.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Deployment Scripts](#deployment-scripts)
- [Docker Configuration](#docker-configuration)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Docker Engine**: 20.10+ 
- **Docker Compose**: 2.0+ (or docker-compose 1.29+)
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: Minimum 20GB free space

### Required Software

```bash
# Check Docker installation
docker --version
docker compose version

# Check system resources
docker system info
```

## 🔐 Environment Configuration

### 1. Environment Variables Setup

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

### 2. Required Environment Variables

#### Development Environment
```env
# Application
DEBUG=True
ENVIRONMENT=development
SECRET_KEY=your-development-secret-key

# Database
DATABASE_URL=sqlite:///database/androidzen.db
# OR for PostgreSQL in development
DATABASE_URL=postgresql://androidzen_user:dev_password@postgres:5432/androidzen

# Redis
REDIS_URL=redis://:dev_redis_password@redis:6379/0
```

#### Production Environment
```env
# Application
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=your-highly-secure-production-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# Database
POSTGRES_DB=androidzen
POSTGRES_USER=androidzen_user
POSTGRES_PASSWORD=your-secure-database-password

# Redis
REDIS_PASSWORD=your-secure-redis-password

# Security
PRODUCTION_URL=https://your-domain.com
FRONTEND_URL=https://your-domain.com
```

## 🚀 Development Deployment

### Quick Start

#### Linux/macOS
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start development environment
./scripts/deploy-dev.sh

# With optional tools (pgAdmin, Redis Commander)
./scripts/deploy-dev.sh --tools
```

#### Windows
```powershell
# Start development environment
.\scripts\deploy-dev.ps1

# With optional tools
.\scripts\deploy-dev.ps1 -Tools
```

### Manual Development Deployment

```bash
# 1. Setup environment
cp .env.example .env

# 2. Create required directories
mkdir -p logs uploads database/init database/backups

# 3. Start services
docker compose up -d

# 4. Check service health
docker compose ps
curl http://localhost:8000/health
curl http://localhost:3000
```

### Development Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React application |
| Backend API | http://localhost:8000 | FastAPI backend |
| API Documentation | http://localhost:8000/docs | Swagger UI |
| pgAdmin | http://localhost:8080 | Database management |
| Redis Commander | http://localhost:8081 | Redis management |

## 🏭 Production Deployment

### Production Deployment Script

```bash
# Full production deployment
./scripts/deploy-prod.sh --monitoring --backup

# Skip database backup
./scripts/deploy-prod.sh --skip-backup

# With cleanup after deployment
./scripts/deploy-prod.sh --cleanup
```

### Manual Production Deployment

```bash
# 1. Validate environment
./scripts/deploy-prod.sh --help

# 2. Build production images
docker compose -f docker-compose.prod.yml build --no-cache

# 3. Start production services
docker compose -f docker-compose.prod.yml up -d

# 4. Run database migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 5. Verify deployment
./scripts/health-check.sh docker-compose.prod.yml
```

### Production Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend (Nginx) | 80, 443 | Production web server |
| Backend API | Internal | API backend (not exposed) |
| PostgreSQL | Internal | Production database |
| Redis | Internal | Cache and sessions |
| Prometheus | 9090 | Monitoring (optional) |
| Grafana | 3001 | Dashboards (optional) |

## 📜 Deployment Scripts

### Available Scripts

| Script | Purpose | Platform |
|--------|---------|----------|
| `deploy-dev.sh` | Development deployment | Linux/macOS |
| `deploy-dev.ps1` | Development deployment | Windows |
| `deploy-prod.sh` | Production deployment | Linux/macOS |
| `backup.sh` | Database backup | Linux/macOS |
| `health-check.sh` | System health monitoring | Linux/macOS |

### Script Options

#### Development Deployment
```bash
./scripts/deploy-dev.sh [OPTIONS]
  --tools     Start optional tools (pgAdmin, Redis Commander)
  --help      Show help message
```

#### Production Deployment
```bash
./scripts/deploy-prod.sh [OPTIONS]
  --skip-backup    Skip database backup before deployment
  --monitoring     Enable monitoring services
  --backup         Enable automated backup service
  --cleanup        Clean up old Docker images
  --help          Show help message
```

## 🐳 Docker Configuration

### Docker Compose Files

| File | Purpose | Environment |
|------|---------|-------------|
| `docker-compose.yml` | Development environment | Development |
| `docker-compose.prod.yml` | Production environment | Production |

### Docker Images

#### Backend Image (Multi-stage)
```dockerfile
# Development target
docker build --target development -t androidzen-backend:dev .

# Production target
docker build --target production -t androidzen-backend:prod .

# Testing target
docker build --target testing -t androidzen-backend:test .
```

#### Frontend Image (Multi-stage)
```dockerfile
# Development target
docker build --target development -t androidzen-frontend:dev ./frontend/

# Production target
docker build --target production -t androidzen-frontend:prod ./frontend/
```

### Docker Profiles

#### Development Profiles
```bash
# Start with optional tools
docker compose --profile tools up -d
```

#### Production Profiles
```bash
# Start with monitoring
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# Start with backup service
docker compose -f docker-compose.prod.yml --profile backup up -d
```

## 📊 Monitoring and Health Checks

### Health Check Script

```bash
# Comprehensive health check
./scripts/health-check.sh

# Quick health check
./scripts/health-check.sh --quick

# JSON output for monitoring systems
./scripts/health-check.sh --json
```

### Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Backend API health |
| `GET /nginx_status` | Nginx status (production) |
| `GET /health` | Frontend health check |

### Monitoring Services (Optional)

- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Visualization dashboards (port 3001)
- **Loki**: Log aggregation

## 🔄 Backup and Recovery

### Automated Backups

```bash
# Manual backup
./scripts/backup.sh

# Test database connectivity
./scripts/backup.sh --test

# Cleanup old backups only
./scripts/backup.sh --cleanup

# Restore from backup
./scripts/backup.sh --restore /backups/backup_file.sql.gz
```

### Backup Configuration

Environment variables for backup script:
```env
BACKUP_DIR=/backups
RETENTION_DAYS=7
MAX_BACKUPS=30
NOTIFICATION_EMAIL=admin@example.com
NOTIFICATION_WEBHOOK=https://hooks.slack.com/...
```

### Backup Schedule

The production deployment includes an automated backup service that runs every 6 hours.

## 🛠️ Troubleshooting

### Common Issues

#### Docker Issues
```bash
# Check Docker daemon
docker info

# Check container logs
docker compose logs [service_name]

# Restart services
docker compose restart [service_name]
```

#### Database Connection Issues
```bash
# Check database status
docker compose exec postgres pg_isready -U androidzen_user -d androidzen

# Check database logs
docker compose logs postgres
```

#### Frontend Build Issues
```bash
# Rebuild frontend container
docker compose build --no-cache frontend

# Check frontend logs
docker compose logs frontend
```

#### Permission Issues (Linux)
```bash
# Fix file permissions
sudo chown -R $USER:$USER logs/ uploads/ database/
chmod -R 755 logs/ uploads/ database/
```

### Service Recovery

```bash
# Stop all services
docker compose down

# Remove containers and volumes (⚠️ DATA LOSS)
docker compose down -v

# Restart from clean state
./scripts/deploy-dev.sh
```

### Log Locations

| Service | Log Location |
|---------|-------------|
| Backend | `logs/app.log` |
| Nginx | Container logs |
| PostgreSQL | Container logs |
| Redis | Container logs |

### Getting Help

1. Check service logs: `docker compose logs [service_name]`
2. Run health check: `./scripts/health-check.sh`
3. Check system resources: `docker system df`
4. Review environment variables: `docker compose config`

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Use strong secret keys (32+ characters)
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Enable Docker security scanning
- [ ] Configure log monitoring
- [ ] Set up automated backups
- [ ] Review CORS settings
- [ ] Enable rate limiting

### Security Headers

The production Nginx configuration includes:
- Content Security Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Strict-Transport-Security

### Network Security

- Services communicate through isolated Docker networks
- No unnecessary port exposure
- Rate limiting on API endpoints
- Authentication required for admin interfaces

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Deployment Guide](https://create-react-app.dev/docs/deployment/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)

## 📞 Support

For deployment issues or questions:
1. Check the troubleshooting section above
2. Review application logs
3. Create an issue in the project repository
4. Contact the development team

---

**Note**: This deployment guide assumes a containerized environment using Docker. For non-containerized deployments, refer to the individual service documentation for installation and configuration instructions.
