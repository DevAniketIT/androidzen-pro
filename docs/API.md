# API Documentation

This document provides an overview of the AndroidZen Pro API endpoints and usage.

## Quick Reference

- **API Documentation**: See [api/API.md](api/API.md) for complete API reference
- **Database Schema**: See [api/DATABASE.md](api/DATABASE.md) for database design
- **Base URL**: 
  - Development: `http://localhost:8000`
  - Production: `https://api.yourdomain.com`

## Authentication

All API endpoints require JWT authentication:

```bash
Authorization: Bearer <your-jwt-token>
```

## Getting Started

1. **Get an access token**: POST to `/api/auth/login` with credentials
2. **Use the token**: Include in Authorization header for all requests
3. **Explore endpoints**: Visit `/docs` for interactive API documentation

## Key Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/api/auth/login` | POST | User authentication |
| `/api/devices` | GET | List managed devices |
| `/api/devices/{id}` | GET | Get device details |
| `/api/analytics` | GET | Device analytics |

For detailed API documentation, see [api/API.md](api/API.md).
