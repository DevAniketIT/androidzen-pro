# Multi-stage Dockerfile for AndroidZen Pro Backend
# Supports both development and production builds

# ============================================================================
# Base Python Image
# ============================================================================
FROM python:3.11-slim as python-base

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.6.1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==$POETRY_VERSION

# Create app user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# ============================================================================
# Dependencies Stage
# ============================================================================
FROM python-base as dependencies

# Set work directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-core.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Development Stage
# ============================================================================
FROM dependencies as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    git \
    vim \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/database /app/backups && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . /app/

# Switch to app user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command for development
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Production Dependencies Stage
# ============================================================================
FROM dependencies as prod-dependencies

# Install additional production dependencies
RUN pip install --no-cache-dir \
    gunicorn \
    uvicorn[standard] \
    psycopg2-binary

# ============================================================================
# Production Stage
# ============================================================================
FROM python-base as production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from prod-dependencies stage
COPY --from=prod-dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=prod-dependencies /usr/local/bin /usr/local/bin

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/database /app/backups && \
    chown -R appuser:appuser /app

# Set work directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser requirements.txt requirements-core.txt ./

# Copy any additional configuration files
COPY --chown=appuser:appuser database/ ./database/

# Switch to app user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with Gunicorn
CMD ["gunicorn", "backend.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]

# ============================================================================
# Testing Stage
# ============================================================================
FROM development as testing

# Install testing dependencies
COPY backend/requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy test files
COPY --chown=appuser:appuser tests/ ./tests/

# Command to run tests
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=backend", "--cov-report=html", "--cov-report=term"]

# ============================================================================
# Security Scanning Stage (optional)
# ============================================================================
FROM production as security-scan

USER root

# Install security scanning tools
RUN pip install --no-cache-dir \
    bandit \
    safety \
    semgrep

USER appuser

# Run security scans
CMD ["sh", "-c", "bandit -r backend/ -f json -o /app/security-report.json && safety check --json --output /app/safety-report.json"]

# ============================================================================
# Build Arguments and Labels
# ============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL maintainer="AndroidZen Pro Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="AndroidZen Pro Backend" \
      org.label-schema.description="FastAPI backend for AndroidZen Pro" \
      org.label-schema.url="https://androidzen-pro.com" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-org/androidzen-pro" \
      org.label-schema.vendor="AndroidZen Pro" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"
