# Build and serve stage - NO NGINX
FROM node:18-slim

# Set working directory
WORKDIR /app

# Accept build arguments
ARG VITE_API_BASE_URL
ARG VITE_CLERK_PUBLISHABLE_KEY

# Set environment variables for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_CLERK_PUBLISHABLE_KEY=${VITE_CLERK_PUBLISHABLE_KEY}

# Copy package files
COPY package*.json ./

# Install dependencies including serve for static file serving
RUN npm ci --include=dev --legacy-peer-deps && npm install -g serve

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Use serve to host the static files (SPA-friendly)
CMD ["serve", "-s", "dist", "-l", "3000"] 