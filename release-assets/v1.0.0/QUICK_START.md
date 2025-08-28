# AndroidZen Pro v1.0.0 - Quick Start Guide

Welcome to AndroidZen Pro! This guide will get you up and running in minutes.

## 🚀 Prerequisites

Before you start, ensure you have:

- **Docker Engine 20.10+** and **Docker Compose 2.0+**
- **4GB+ RAM** available (8GB+ recommended)
- **20GB+ free disk space**
- **Internet connection** for downloading dependencies

## ⚡ 5-Minute Setup

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-org/androidzen-pro.git
cd androidzen-pro

# Copy environment template
cp .env.example .env
```

### 2. Start Services
```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait for services to be ready (usually 1-2 minutes)
```

### 3. Verify Installation
```bash
# Run the verification script
chmod +x release-assets/v1.0.0/verify-installation.sh
./release-assets/v1.0.0/verify-installation.sh
```

### 4. Access Applications
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 🔧 First Steps

### Create Admin User
```bash
# Create your first admin user
docker-compose exec backend python -c "
from backend.models.user import User
from backend.core.database import get_db
from backend.core.auth import get_password_hash

# Replace with your details
admin_user = User(
    username='admin',
    email='admin@yourcompany.com',
    hashed_password=get_password_hash('your_secure_password'),
    is_admin=True,
    is_active=True
)
print('Admin user created successfully!')
"
```

### Test API Access
```bash
# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

## 📱 Key Features Available

### Device Management
- Enroll Android devices using Google Zero Touch
- Configure work profiles for BYOD scenarios
- Apply security policies and compliance rules
- Monitor device health and performance

### Security & Analytics
- Real-time security monitoring
- AI-powered anomaly detection
- Performance analytics and optimization
- Comprehensive audit logging

### Administration
- Role-based access control
- Multi-tenant support
- API-first architecture
- WebSocket real-time updates

## 🔗 Essential Endpoints

| Feature | Endpoint | Description |
|---------|----------|-------------|
| **API Docs** | `/docs` | Interactive API documentation |
| **Health Check** | `/health` | System health status |
| **Authentication** | `/api/auth/login` | User authentication |
| **Devices** | `/api/devices/` | Device management |
| **Analytics** | `/api/ai/analytics/` | AI-powered insights |
| **Security** | `/api/security/events` | Security monitoring |

## 🛡️ Security Configuration

### Default Settings (Development)
```env
# Basic security settings in .env
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=jwt-dev-secret-key

# Database
DATABASE_URL=sqlite:///./database/androidzen.db

# Redis (optional for development)
REDIS_URL=redis://localhost:6379/0
```

### Production Security
For production deployment:
1. Generate strong secret keys
2. Configure SSL certificates
3. Set up proper firewall rules
4. Enable monitoring and alerting

## 📊 Monitoring & Logs

### View Service Status
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Health Monitoring
```bash
# API health check
curl http://localhost:8000/health

# WebSocket stats
curl http://localhost:8000/ws/stats
```

## 🔄 Common Commands

### Service Management
```bash
# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Update and rebuild
docker-compose pull && docker-compose up -d --build
```

### Database Operations
```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Check database status
docker-compose exec postgres pg_isready
```

## 🐛 Troubleshooting

### Services Not Starting
```bash
# Check service logs
docker-compose logs

# Restart with verbose output
docker-compose up --no-daemon
```

### Port Conflicts
If ports 3000 or 8000 are in use:
```bash
# Stop conflicting services or modify ports in docker-compose.yml
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :8000
```

### Database Issues
```bash
# Reset database (⚠️ DATA LOSS)
docker-compose down -v
docker-compose up -d
```

## 📚 Next Steps

### Development
- Read the [Contributing Guide](../../CONTRIBUTING.md)
- Explore the [API Documentation](../../API.md)
- Set up your development environment

### Production Deployment
- Review the [Deployment Guide](../../DEPLOYMENT.md)
- Configure SSL certificates and security
- Set up monitoring and backups

### Integration
- Connect your Android devices
- Configure policies and compliance rules
- Set up user accounts and roles

## 🎯 Success Indicators

You should see:
- ✅ All services running (`docker-compose ps`)
- ✅ Frontend accessible at http://localhost:3000
- ✅ API docs at http://localhost:8000/docs
- ✅ Health check returning "healthy" status
- ✅ No error messages in logs

## 📞 Getting Help

### Documentation
- **Complete Guide**: [README.md](../../README.md)
- **API Reference**: [API.md](../../API.md)
- **Deployment**: [DEPLOYMENT.md](../../DEPLOYMENT.md)
- **Security**: [SECURITY.md](../../SECURITY.md)

### Support
- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Security Issues**: Email security@androidzen-pro.com

## 🎉 Congratulations!

You now have AndroidZen Pro running locally. Start by:

1. **Exploring the Frontend**: http://localhost:3000
2. **Reading API Docs**: http://localhost:8000/docs
3. **Creating Your First Device Policy**
4. **Setting Up User Accounts**

**Happy device managing!** 📱✨

---

**AndroidZen Pro v1.0.0**  
*Production-Ready Android Enterprise Management*
