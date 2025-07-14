# Cliplink Unified Deployment Guide

This guide covers the unified deployment system where both frontend (React) and backend (FastAPI) are served from a single container, as recommended for production deployments.

## 🏗️ Architecture Overview

The unified system consists of:
- **Single App Container**: React frontend + FastAPI backend
- **PostgreSQL Database**: For persistent data storage
- **Redis**: For caching and task queues
- **Optional Nginx**: For SSL termination and load balancing

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git (for cloning the repository)
- curl (for health checks)

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd cliplink
```

### 2. Deploy Using Script
```bash
chmod +x deploy-unified.sh
./deploy-unified.sh
```

The script will:
- Check prerequisites
- Create environment configuration
- Build the unified container
- Start all services
- Run health checks
- Provide access URLs

### 3. Access Your Application
- **Frontend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 File Structure

```
cliplink/
├── Dockerfile                    # Unified multi-stage build
├── docker-compose.unified.yml    # Production-ready compose file
├── production.env.example        # Environment template
├── deploy-unified.sh            # Deployment script
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py             # Updated to serve frontend
│   │   └── ...
│   └── requirements.txt        # Fixed dependencies
├── frontend/                   # React application
│   ├── src/
│   │   └── components/         # Updated with relative URLs
│   └── package.json
└── README-UNIFIED-DEPLOYMENT.md
```

## 🔧 Manual Deployment

If you prefer manual deployment:

### 1. Environment Configuration
```bash
cp production.env.example .env
# Edit .env with your actual values
```

### 2. Build and Start
```bash
docker-compose -f docker-compose.unified.yml build
docker-compose -f docker-compose.unified.yml up -d
```

### 3. Health Checks
```bash
# Check application
curl http://localhost:8000/health

# Check frontend
curl http://localhost:8000/

# Check API
curl http://localhost:8000/docs
```

## 🌐 Production Deployment

### Azure App Service
1. Build and push to Azure Container Registry:
```bash
# Build image
docker build -t your-registry.azurecr.io/cliplink:latest .

# Push to registry
docker push your-registry.azurecr.io/cliplink:latest
```

2. Create App Service with container image
3. Configure environment variables in Azure portal
4. Enable autoscaling rules

### Azure Container Apps
1. Use the same container image
2. Configure environment variables
3. Set up autoscaling triggers (CPU, memory, HTTP requests)

### Azure VM with Docker
1. Copy files to VM
2. Run deployment script
3. Configure domain and SSL
4. Set up monitoring

## 🔐 Environment Variables

### Required Variables
```bash
# Database
DB_PASSWORD=your-secure-password
DATABASE_URL=postgresql+asyncpg://cliplink:password@db:5432/cliplink

# Authentication
CLERK_DOMAIN=your-domain.clerk.accounts.dev
VITE_CLERK_PUBLISHABLE_KEY=pk_live_your-key
JWKS_URL=https://your-domain.clerk.accounts.dev/.well-known/jwks.json

# External Services
GROQ_API_KEY=your-groq-api-key
AZURE_STORAGE_CONNECTION_STRING=your-azure-connection-string
```

### Optional Variables
```bash
# Performance
UVICORN_WORKERS=1
APP_PORT=8000

# Security
ALLOWED_ORIGINS=https://your-domain.com
SECRET_KEY=your-secret-key

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

## 📊 Monitoring and Logging

### View Logs
```bash
# All services
docker-compose -f docker-compose.unified.yml logs -f

# Specific service
docker-compose -f docker-compose.unified.yml logs -f app
```

### Health Monitoring
The application includes built-in health checks:
- `/health` - Overall application health
- Database connectivity check
- Redis connectivity check

### Metrics
Enable metrics collection by setting:
```bash
ENABLE_METRICS=true
```

## 🔧 Troubleshooting

### Common Issues

1. **Frontend not loading**
   - Check if `FRONTEND_DIST_PATH=/app/frontend/dist` is set
   - Verify frontend build was successful in Docker logs

2. **API calls failing**
   - Check CORS configuration in `ALLOWED_ORIGINS`
   - Verify authentication tokens are valid

3. **Database connection issues**
   - Check `DATABASE_URL` format
   - Verify PostgreSQL container is healthy

4. **Azure storage issues**
   - Verify Azure credentials are correct
   - Check container/blob permissions

### Debug Commands
```bash
# Check container status
docker-compose -f docker-compose.unified.yml ps

# Access container shell
docker-compose -f docker-compose.unified.yml exec app bash

# Check database
docker-compose -f docker-compose.unified.yml exec db psql -U cliplink -d cliplink

# Restart services
docker-compose -f docker-compose.unified.yml restart
```

## 📈 Scaling

### Horizontal Scaling
For Azure App Service or Container Apps:
1. Enable autoscaling in Azure portal
2. Configure scale rules (CPU, memory, HTTP requests)
3. Set minimum and maximum instances

### Vertical Scaling
Update resource limits in docker-compose.unified.yml:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
```

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and redeploy
docker-compose -f docker-compose.unified.yml build --no-cache
docker-compose -f docker-compose.unified.yml up -d
```

### Database Migrations
```bash
# Run migrations
docker-compose -f docker-compose.unified.yml exec app python -m alembic upgrade head
```

### Backup
```bash
# Database backup
docker-compose -f docker-compose.unified.yml exec db pg_dump -U cliplink cliplink > backup.sql
```

## 📝 Key Differences from Separate Deployment

1. **Single Container**: Frontend and backend in one container
2. **Relative URLs**: Frontend uses relative paths (e.g., `/api/users/me`)
3. **Simplified CORS**: No cross-origin issues
4. **Easier SSL**: One certificate for both frontend and API
5. **Simpler Networking**: No inter-container communication needed

## 🎯 Benefits

✅ **Simplified Deployment**: One container to manage  
✅ **No CORS Issues**: Everything served from same origin  
✅ **Easier SSL Setup**: Single certificate  
✅ **Better Performance**: No cross-origin requests  
✅ **Unified Logging**: All logs in one place  
✅ **Simpler Scaling**: Scale both together  

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs
3. Verify environment configuration
4. Test with minimal configuration

This unified deployment approach provides a production-ready, scalable solution for your Cliplink application. 