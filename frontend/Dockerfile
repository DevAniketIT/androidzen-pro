# Multi-stage Dockerfile for AndroidZen Pro Frontend
# Supports both development and production builds

# ============================================================================
# Base Node.js Image
# ============================================================================
FROM node:18-alpine as node-base

# Set working directory
WORKDIR /app

# Install dependencies for better performance
RUN apk add --no-cache \
    git \
    curl

# Create app user
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser

# ============================================================================
# Dependencies Stage
# ============================================================================
FROM node-base as dependencies

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# ============================================================================
# Development Dependencies Stage
# ============================================================================
FROM node-base as dev-dependencies

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies)
RUN npm ci && \
    npm cache clean --force

# ============================================================================
# Development Stage
# ============================================================================
FROM dev-dependencies as development

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to app user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start development server
CMD ["npm", "start"]

# ============================================================================
# Build Stage
# ============================================================================
FROM dev-dependencies as build

# Set build environment
ARG NODE_ENV=production
ARG REACT_APP_API_URL
ARG REACT_APP_WS_URL
ARG REACT_APP_VERSION

ENV NODE_ENV=$NODE_ENV
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL
ENV REACT_APP_VERSION=$REACT_APP_VERSION

# Copy source code
COPY . .

# Build the application
RUN npm run build

# ============================================================================
# Production Stage (Nginx)
# ============================================================================
FROM nginx:1.25-alpine as production

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default Nginx configuration
RUN rm -rf /etc/nginx/conf.d

# Create nginx user and directories
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser && \
    mkdir -p /var/cache/nginx && \
    mkdir -p /var/run && \
    mkdir -p /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/run && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /etc/nginx

# Copy built application from build stage
COPY --from=build --chown=appuser:appuser /app/build /usr/share/nginx/html

# Copy custom Nginx configuration
COPY --chown=appuser:appuser nginx.conf /etc/nginx/nginx.conf

# Create a script to substitute environment variables at runtime
RUN cat > /docker-entrypoint.sh << 'EOF'
#!/bin/sh
set -e

# Function to replace environment variables in JS files
replace_env_vars() {
    echo "Replacing environment variables..."
    
    # Replace API URL
    if [ -n "$REACT_APP_API_URL" ]; then
        find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__API_URL__|$REACT_APP_API_URL|g" {} +
    fi
    
    # Replace WebSocket URL
    if [ -n "$REACT_APP_WS_URL" ]; then
        find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__WS_URL__|$REACT_APP_WS_URL|g" {} +
    fi
    
    # Replace Version
    if [ -n "$REACT_APP_VERSION" ]; then
        find /usr/share/nginx/html -name "*.js" -exec sed -i "s|__VERSION__|$REACT_APP_VERSION|g" {} +
    fi
}

# Replace environment variables
replace_env_vars

# Start Nginx
exec "$@"
EOF

RUN chmod +x /docker-entrypoint.sh && \
    chown appuser:appuser /docker-entrypoint.sh

# Switch to app user
USER appuser

# Expose port
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start Nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

# ============================================================================
# Testing Stage
# ============================================================================
FROM dev-dependencies as testing

# Copy source code
COPY . .

# Run tests
CMD ["npm", "test", "--", "--coverage", "--watchAll=false"]

# ============================================================================
# Linting Stage
# ============================================================================
FROM dev-dependencies as linting

# Copy source code
COPY . .

# Run linting and formatting checks
CMD ["sh", "-c", "npm run lint && npm run format:check && npm run type-check"]

# ============================================================================
# Security Scanning Stage
# ============================================================================
FROM dev-dependencies as security-scan

# Copy source code
COPY . .

# Run security audit
CMD ["sh", "-c", "npm audit --audit-level=moderate && npm run security:scan"]

# ============================================================================
# Build Arguments and Labels
# ============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL maintainer="AndroidZen Pro Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="AndroidZen Pro Frontend" \
      org.label-schema.description="React frontend for AndroidZen Pro" \
      org.label-schema.url="https://androidzen-pro.com" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-org/androidzen-pro" \
      org.label-schema.vendor="AndroidZen Pro" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"
