# Cliplink Deployment Guide

Complete guide for deploying the Cliplink full stack application to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Docker Deployment](#docker-deployment)
5. [Traditional Deployment](#traditional-deployment)
6. [Production Optimization](#production-optimization)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Server**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 50GB SSD (for video processing)
- **CPU**: 2+ cores (4+ recommended for video processing)

### Software Dependencies

- Docker & Docker Compose
- Node.js 18+ (for traditional deployment)
- Python 3.12+ (for traditional deployment)
- PostgreSQL 15+ (for traditional deployment)
- Nginx (for reverse proxy)
- FFmpeg (for video processing)

### External Services

- **Clerk Account**: For authentication
- **Groq API Key**: For AI transcription
- **YouTube Data API**: For video metadata
- **Domain & SSL Certificate**: For production

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/cliplink.git
cd cliplink
```

### 2. Environment Variables

Create environment files from templates:

```bash
# Backend environment
cp backend/env.example backend/.env
# Edit backend/.env with your values

# Frontend environment
cp frontend/env.example frontend/.env
# Edit frontend/.env with your values

# Docker environment
cp .env.example .env
# Edit .env with your values
```

### 3. Required Environment Variables

#### Backend (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://username:password@host:5432/cliplink

# Clerk Authentication
CLERK_DOMAIN=your-domain.clerk.accounts.dev
JWKS_URL=https://your-domain.clerk.accounts.dev/.well-known/jwks.json

# API Keys
GROQ_API_KEY=your-groq-api-key
YOUTUBE_TRANSCRIPT_API=your-youtube-api-key

# Security
ALLOWED_ORIGINS=https://your-domain.com

# Application
DEBUG=false
LOG_LEVEL=INFO
```

#### Frontend (.env)
```env
# Clerk Authentication
VITE_CLERK_PUBLISHABLE_KEY=pk_live_your-publishable-key

# API Configuration
VITE_API_BASE_URL=https://your-api-domain.com

# Application
VITE_APP_NAME=Cliplink
```

## Database Setup

### 1. Create Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE cliplink;
CREATE USER cliplink WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE cliplink TO cliplink;
```

### 2. Run Schema

```bash
# Apply database schema
psql -U cliplink -d cliplink -f backend/schema.sql
```

### 3. Verify Setup

```bash
# Test database connection
psql -U cliplink -d cliplink -c "SELECT * FROM users LIMIT 1;"
```

## Docker Deployment (Recommended)

### 1. Prepare Environment

```bash
# Create Docker environment file
cat > .env << EOF
DB_PASSWORD=your-secure-db-password
CLERK_DOMAIN=your-domain.clerk.accounts.dev
JWKS_URL=https://your-domain.clerk.accounts.dev/.well-known/jwks.json
VITE_CLERK_PUBLISHABLE_KEY=pk_live_your-publishable-key
VITE_API_BASE_URL=https://your-api-domain.com
ALLOWED_ORIGINS=https://your-domain.com
GROQ_API_KEY=your-groq-api-key
YOUTUBE_TRANSCRIPT_API=your-youtube-api-key
EOF
```

### 2. Build and Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:80/health

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Traditional Deployment

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://..."
export CLERK_DOMAIN="your-domain.clerk.accounts.dev"
# ... other variables

# Start application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Serve with nginx or serve static files
# Copy dist/ folder to your web server
```

### 3. Nginx Configuration

```nginx
# /etc/nginx/sites-available/cliplink
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    # Frontend
    location / {
        root /var/www/cliplink;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /clips {
        proxy_pass http://localhost:8000;
    }

    location /thumbnails {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. System Services

Create systemd service for backend:

```ini
# /etc/systemd/system/cliplink-backend.service
[Unit]
Description=Cliplink Backend
After=network.target

[Service]
Type=simple
User=cliplink
WorkingDirectory=/opt/cliplink/backend
Environment=PATH=/opt/cliplink/backend/venv/bin
ExecStart=/opt/cliplink/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Production Optimization

### 1. Database Optimization

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
SELECT pg_reload_conf();
```

### 2. Application Optimization

```python
# Backend: Use connection pooling
# In database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300,
)
```

### 3. Caching Strategy

```bash
# Redis for caching
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Backend caching implementation
pip install redis aioredis
```

### 4. CDN Configuration

```javascript
// Frontend: Configure CDN for static assets
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
})
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Ubuntu UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/TLS Setup

```bash
# Let's Encrypt with Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo certbot renew --dry-run
```

### 3. Security Headers

```nginx
# Add to nginx configuration
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

## Monitoring & Maintenance

### 1. Health Checks

```bash
# Backend health
curl -f http://localhost:8000/health || exit 1

# Frontend health
curl -f http://localhost/health || exit 1

# Database health
pg_isready -U cliplink -d cliplink
```

### 2. Logging

```bash
# Docker logs
docker-compose logs -f --tail=100 backend
docker-compose logs -f --tail=100 frontend

# System logs
journalctl -u cliplink-backend -f
```

### 3. Backup Strategy

```bash
# Database backup
pg_dump -U cliplink -d cliplink > backup_$(date +%Y%m%d_%H%M%S).sql

# Files backup
tar -czf clips_backup_$(date +%Y%m%d).tar.gz backend/downloads/
```

### 4. Performance Monitoring

```bash
# Install monitoring tools
pip install prometheus-client
npm install @sentry/react @sentry/node

# Resource monitoring
htop
iotop
netstat -tulpn
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connections
   netstat -an | grep 5432
   
   # Test connection
   psql -U cliplink -d cliplink -c "SELECT version();"
   ```

2. **Authentication Issues**
   ```bash
   # Verify Clerk configuration
   curl -s https://your-domain.clerk.accounts.dev/.well-known/jwks.json
   
   # Check environment variables
   env | grep CLERK
   ```

3. **File Upload Issues**
   ```bash
   # Check permissions
   ls -la backend/downloads/
   
   # Check disk space
   df -h
   
   # Check FFmpeg
   ffmpeg -version
   ```

4. **Performance Issues**
   ```bash
   # Monitor resources
   top
   iotop
   
   # Check database queries
   SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

### Maintenance Tasks

1. **Regular Updates**
   ```bash
   # Update dependencies
   pip install -r requirements.txt --upgrade
   npm update
   
   # Update Docker images
   docker-compose pull
   docker-compose up -d
   ```

2. **Database Maintenance**
   ```sql
   -- Analyze tables
   ANALYZE;
   
   -- Vacuum tables
   VACUUM ANALYZE;
   
   -- Check for dead tuples
   SELECT schemaname, tablename, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 0;
   ```

3. **Log Rotation**
   ```bash
   # Configure logrotate
   sudo vi /etc/logrotate.d/cliplink
   
   /var/log/cliplink/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       postrotate
           systemctl reload cliplink-backend
       endscript
   }
   ```

## Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Database schema applied
- [ ] SSL certificates installed
- [ ] Domain DNS configured
- [ ] Firewall rules set
- [ ] Backup strategy implemented

### Post-Deployment
- [ ] Health checks passing
- [ ] Authentication working
- [ ] File uploads working
- [ ] Video processing working
- [ ] Performance monitoring active
- [ ] Log aggregation configured
- [ ] Backup tested

### Security
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Database access restricted
- [ ] API keys secured
- [ ] File permissions correct
- [ ] Vulnerability scan completed

---

For additional support, refer to the individual service documentation:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Workflow Documentation](backend/COMPREHENSIVE_WORKFLOW_README.md) 