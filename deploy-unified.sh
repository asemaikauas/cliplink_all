#!/bin/bash

# Unified Cliplink Deployment Script
# This script deploys the unified frontend + backend system

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

print_header "🚀 Cliplink Unified Deployment Script"
print_header "======================================"

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
    sed -i.bak "s/ad7Vgy26/$db_password/g" .env
    sed -i.bak "s/https://deep-starling-83.clerk.accounts.dev/$clerk_domain/g" .env
    sed -i.bak "s/pk_test_ZGVlcC1zdGFybGluZy04My5jbGVyay5hY2NvdW50cy5kZXYk/$clerk_publishable_key/g" .env
    sed -i.bak "s/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/$groq_api_key/g" .env
    
    # Update JWKS URL
    jwks_url="https://$clerk_domain/.well-known/jwks.json"
    sed -i.bak "s|https://deep-starling-83.clerk.accounts.dev/.well-known/jwks.json|$jwks_url|g" .env
    
    rm .env.bak
    
    print_status "✅ Environment file configured"
else
    print_warning "Environment file already exists. Using existing configuration."
fi

# Build and deploy
print_status "Building unified application..."
docker-compose -f docker-compose.unified.yml build --no-cache

print_status "Starting services..."
docker-compose -f docker-compose.unified.yml up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 45

# Health checks
print_status "Performing health checks..."

# Check database
if docker-compose -f docker-compose.unified.yml exec db pg_isready -U cliplink > /dev/null 2>&1; then
    print_status "✅ Database health check passed"
else
    print_error "❌ Database health check failed"
    docker-compose -f docker-compose.unified.yml logs db
    exit 1
fi

# Check Redis
if docker-compose -f docker-compose.unified.yml exec redis redis-cli ping > /dev/null 2>&1; then
    print_status "✅ Redis health check passed"
else
    print_error "❌ Redis health check failed"
    docker-compose -f docker-compose.unified.yml logs redis
    exit 1
fi

# Check application
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "✅ Application health check passed"
else
    print_error "❌ Application health check failed"
    docker-compose -f docker-compose.unified.yml logs app
    exit 1
fi

# Check frontend
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    print_status "✅ Frontend health check passed"
else
    print_error "❌ Frontend health check failed"
    docker-compose -f docker-compose.unified.yml logs app
    exit 1
fi

print_header "🎉 Deployment completed successfully!"
print_header "=================================="
print_status "Application URL: http://localhost:8000"
print_status "API Documentation: http://localhost:8000/docs"
print_status "Health Check: http://localhost:8000/health"
print_status ""
print_status "Container Status:"
docker-compose -f docker-compose.unified.yml ps

print_status ""
print_status "To view logs: docker-compose -f docker-compose.unified.yml logs -f"
print_status "To stop: docker-compose -f docker-compose.unified.yml down"
print_status "To restart: docker-compose -f docker-compose.unified.yml restart"

print_header "🔧 Next Steps for Production:"
print_status "1. Update your DNS to point to this server's IP"
print_status "2. Configure SSL certificates (Let's Encrypt recommended)"
print_status "3. Set up monitoring and backup systems"
print_status "4. Configure autoscaling if needed"
print_status "5. Test the application thoroughly" 