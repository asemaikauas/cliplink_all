#!/bin/bash

# Separate Frontend/Backend Cliplink Deployment Script
# This script deploys frontend and backend as separate containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to prompt for input
prompt_input() {
    read -p "$1: " value
    echo "$value"
}

# Function to prompt for password
prompt_password() {
    read -s -p "$1: " value
    echo
    echo "$value"
}

print_header "🚀 Cliplink Separate Frontend/Backend Deployment"
print_header "=============================================="

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "✅ Prerequisites check passed"

# Check if environment file exists
if [ ! -f .env ]; then
    print_status "Creating environment file from template..."
    
    if [ -f production.env.example ]; then
        cp production.env.example .env
        print_warning "Environment file created from template. Please edit .env with your actual values."
    else
        print_error "production.env.example not found. Please create it first."
        exit 1
    fi
    
    echo
    print_status "Please provide the following configuration values:"
    
    # Collect essential configuration
    db_password=$(prompt_password "Database password")
    clerk_domain=$(prompt_input "Clerk domain (e.g., your-app.clerk.accounts.dev)")
    clerk_publishable_key=$(prompt_input "Clerk publishable key")
    your_domain=$(prompt_input "Your domain (e.g., your-domain.com)")
    groq_api_key=$(prompt_password "Groq API key")
    
    # Update environment file
    sed -i.bak "s/your-secure-database-password-here/$db_password/g" .env
    sed -i.bak "s/your-domain.clerk.accounts.dev/$clerk_domain/g" .env
    sed -i.bak "s/pk_live_your-publishable-key-here/$clerk_publishable_key/g" .env
    sed -i.bak "s/your-groq-api-key-here/$groq_api_key/g" .env
    
    # Update JWKS URL
    jwks_url="https://$clerk_domain/.well-known/jwks.json"
    sed -i.bak "s|https://your-domain.clerk.accounts.dev/.well-known/jwks.json|$jwks_url|g" .env
    
    rm .env.bak
    
    print_status "✅ Environment file configured"
else
    print_warning "Environment file already exists. Using existing configuration."
fi

# Build frontend first
print_status "Building frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install
fi

print_status "Building React application..."
npm run build

# Verify dist folder exists
if [ ! -d "dist" ]; then
    print_error "Frontend build failed - dist folder not found"
    exit 1
fi

cd ..

# Build and deploy containers
print_status "Building backend container..."
docker-compose build backend

print_status "Building frontend container..."
docker-compose build frontend

print_status "Starting all services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 45

# Health checks
print_status "Performing health checks..."

# Check database
if docker-compose exec db pg_isready -U cliplink > /dev/null 2>&1; then
    print_status "✅ Database health check passed"
else
    print_error "❌ Database health check failed"
    docker-compose logs db
    exit 1
fi

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    print_status "✅ Redis health check passed"
else
    print_error "❌ Redis health check failed"
    docker-compose logs redis
    exit 1
fi

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "✅ Backend health check passed"
else
    print_error "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi

# Check frontend
if curl -f http://localhost:3000/ > /dev/null 2>&1; then
    print_status "✅ Frontend health check passed"
else
    print_error "❌ Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi

print_header "🎉 Deployment completed successfully!"
print_header "=================================="
print_status "Frontend URL: http://localhost:3000"
print_status "Backend API: http://localhost:8000"
print_status "API Documentation: http://localhost:8000/docs"
print_status "Backend Health: http://localhost:8000/health"
print_status ""
print_status "Container Status:"
docker-compose ps

print_status ""
print_status "To view logs:"
print_status "  All services: docker-compose logs -f"
print_status "  Frontend: docker-compose logs -f frontend"
print_status "  Backend: docker-compose logs -f backend"
print_status "  Database: docker-compose logs -f db"
print_status ""
print_status "To stop: docker-compose down"
print_status "To restart: docker-compose restart"

print_header "🔧 Next Steps for Production:"
print_status "1. Configure your frontend to use the production backend URL"
print_status "2. Set up SSL certificates and reverse proxy"
print_status "3. Configure domain names and DNS"
print_status "4. Set up monitoring and backup systems"
print_status "5. Configure autoscaling if needed"
print_status "6. Test the application thoroughly" 