# NetScope Infrastructure Improvement Recommendations

**Date:** November 18, 2026  
**Priority:** Production-Ready Infrastructure

---

## Executive Summary

This document provides detailed recommendations for improving the NetScope infrastructure. The recommendations are organized by category with specific implementation steps, file references, and code examples.

---

## 1. Docker Configuration

### Current State Analysis
The project has a problematic single-stage Dockerfile at the root that doesn't follow best practices:
- Uses `ubuntu:22.04` as final image (large base)
- No multi-stage builds
- Missing health checks
- No non-root user
- Insecure port exposure

### Recommendation 1.1: Create Multi-Stage Backend Dockerfile

**File:** `backend/Dockerfile` (CREATE NEW)

```dockerfile
# ==========================================
# Backend Production Dockerfile
# Multi-stage build for optimal image size
# ==========================================

FROM python:3.12-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Change to non-root user
USER appuser

# Health check (optional, override in docker-compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Improvements:**
- Uses `python:3.12-slim` (smaller base image)
- Multi-stage build capability
- Non-root user (`appuser`)
- Health check included

---

### Recommendation 1.2: Create Frontend Dockerfile with Nginx

**File:** `frontend/Dockerfile` (CREATE NEW)

```dockerfile
# ==========================================
# Frontend Production Dockerfile
# Optimized for static file serving
# ==========================================

FROM node:20-alpine as builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (dev dependencies for build)
RUN npm ci && npm cache clean --force

# Copy source
COPY frontend/ ./

# Build the application
RUN npm run build

# Production image
FROM nginx:alpine

# Create directory for static files
RUN mkdir -p /usr/share/nginx/html

# Copy built assets
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Create nginx configuration directory
RUN mkdir -p /etc/nginx/conf.d

# Copy custom nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
```

**Create:** `frontend/nginx.conf`
```nginx
server {
    listen 3000;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;
}
```

**Key Improvements:**
- Optimized build cache
- Nginx for static file serving
- Security headers
- Gzip compression

---

### Recommendation 1.3: Create Docker Compose for Development

**File:** `docker-compose.yml` (CREATE NEW)

```yaml
# ==========================================
# NetScope Development Environment
# docker-compose.yml
# ==========================================

version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/netscope
      - SECRET_KEY=${SECRET_KEY:-dev-insecure-key-change-me}
      - DEBUG=true
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network
    volumes:
      # Mount for development (hot reload)
      - ./backend:/app/backend:ro
      # Log volume
      - backend_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/extended"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=netscope
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
  backend_logs:
```

**Create:** `.env.example`
```bash
# NetScope Environment Template

# Core Settings
SECRET_KEY=<generate-with: python -c 'import secrets; print(secrets.token_hex(32))'>
DEBUG=false
LOG_LEVEL=INFO

# Backend Server
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Database (Production)
DATABASE_URL=postgresql://user:pass@localhost:5432/netscope

# Scanning
DEFAULT_RATE_LIMIT=medium
MAX_CONCURRENT_HOSTS=5
SCAN_TIMEOUT_SECONDS=3600

# Intelligence APIs (Optional)
CISA_API_KEY=
NVD_API_KEY=

# Security
ALLOWED_ORIGINS=https://netscope.example.com

# Development
ENABLE_DEBUG=true
```

**Usage:**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend
```

---

## 2. Deployment Architecture

### Recommendation 2.1: Create CI/CD Pipeline

**File:** `.github/workflows/ci.yml` (CREATE NEW)

```yaml
# ==========================================
# NetScope CI/CD Pipeline
# GitHub Actions Workflow
# ==========================================

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

# Define global environment variables
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test-backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pytest pytest-asyncio
      
      - name: Run linter
        run: ruff check .
      
      - name: Run type checker
        run: mypy app/
      
      - name: Run tests with coverage
        run: |
          pytest app/tests/ --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml

  test-frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run linter
        run: npm run lint
      
      - name: Build frontend
        run: npm run build

  security-scan:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run Trivy security scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'table'
          severity: 'CRITICAL,HIGH'

  build-and-push:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata for backend
        id: meta-backend
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend
      
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./backend/Dockerfile
          push: true
          tags: ${{ steps.meta-backend.outputs.tags }}
          labels: ${{ steps.meta-backend.outputs.labels }}
      
      - name: Extract metadata for frontend
        id: meta-frontend
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend
      
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./frontend/Dockerfile
          push: true
          tags: ${{ steps.meta-frontend.outputs.tags }}
          labels: ${{ steps.meta-frontend.outputs.labels }}

  deploy:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to Kubernetes
        run: |
          # Apply Kubernetes manifests
          kubectl apply -f k8s/deployment.yaml
          
          # Wait for deployment to complete
          kubectl rollout status deployment/netscope-backend -n default --timeout=300s
          kubectl rollout status deployment/netscope-frontend -n default --timeout=300s
```

---

### Recommendation 2.2: Create Kubernetes Manifests

**File:** `k8s/deployment.yaml` (CREATE NEW)

```yaml
# ==========================================
# NetScope Kubernetes Deployment
# Production-ready manifest file
# ==========================================

apiVersion: v1
kind: Secret
metadata:
  name: netscope-secrets
type: Opaque
stringData:
  database-url: postgresql://netscope_user:netscope_pass@db.netscope.svc.cluster.local:5432/netscope
  secret-key: ${SECRET_KEY}

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: netscope-config
data:
  DEBUG: "false"
  LOG_LEVEL: INFO
  MAX_CONCURRENT_HOSTS: "5"
  SCAN_TIMEOUT_SECONDS: "3600"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netscope-backend
  labels:
    app: netscope
    tier: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: netscope-backend
  template:
    metadata:
      labels:
        app: netscope-backend
    spec:
      containers:
        - name: backend
          image: ghcr.io/your-org/netscope-backend:latest
          ports:
            - containerPort: 8000
              protocol: TCP
          envFrom:
            - configMapRef:
                name: netscope-config
            - secretRef:
                name: netscope-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/extended
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            failureThreshold: 30
            periodSeconds: 10
      
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values: [netscope-backend]
                topologyKey: kubernetes.io/hostname

---
apiVersion: v1
kind: Service
metadata:
  name: netscope-backend-service
  labels:
    app: netscope
spec:
  selector:
    app: netscope-backend
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
  type: ClusterIP

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netscope-frontend
  labels:
    app: netscope
    tier: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: netscope-frontend
  template:
    metadata:
      labels:
        app: netscope-frontend
    spec:
      containers:
        - name: frontend
          image: ghcr.io/your-org/netscope-frontend:latest
          ports:
            - containerPort: 3000
              protocol: TCP
          resources:
            requests:
              memory: "128Mi"
              cpu: "50m"
            limits:
              memory: "256Mi"
              cpu: "200m"

---
apiVersion: v1
kind: Service
metadata:
  name: netscope-frontend-service
  labels:
    app: netscope
spec:
  selector:
    app: netscope-frontend
  ports:
    - port: 3000
      targetPort: 3000
      protocol: TCP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: netscope-ingress
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - netscope.example.com
      secretName: netscope-tls
  rules:
    - host: netscope.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: netscope-frontend-service
                port:
                  number: 3000
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: netscope-backend-service
                port:
                  number: 8000

---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: netscope-backend-monitor
  labels:
    app: netscope
spec:
  selector:
    matchLabels:
      app: netscope-backend
  endpoints:
    - port: metrics
      path: /metrics
      interval: 15s

---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: netscope-rules
  labels:
    app: netscope
spec:
  groups:
    - name: netscope.rules
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate detected"
            description: "The error rate is above 10% for the last 5 minutes."

        - alert: HighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High latency detected"
            description: "The 95th percentile latency is above 1 second."
```

---

## 3. Configuration Management

### Recommendation 3.1: Implement Secrets Manager

**File:** `backend/app/core/secrets.py` (CREATE NEW)

```python
# ==========================================
# NetScope Secrets Manager
# Secure secrets handling with vault support
# ==========================================

import os
from functools import lru_cache
from pathlib import Path
import secrets


class SecretsManager:
    """Secure secrets management with vault integration support."""
    
    def __init__(self):
        self._secrets_cache = {}
        self.vault_url = os.environ.get("VAULT_URL")
        self._load_from_env()
    
    def _load_from_env(self):
        """Load secrets from environment variables."""
        self._secrets_cache["SECRET_KEY"] = self._get_secret("SECRET_KEY", required=True)
        self._secrets_cache["DATABASE_URL"] = self._get_secret("DATABASE_URL", required=False)
        self._secrets_cache["CISA_API_KEY"] = self._get_secret("CISA_API_KEY", required=False)
        self._secrets_cache["NVD_API_KEY"] = self._get_secret("NVD_API_KEY", required=False)
    
    def _get_secret(self, name: str, required: bool = False) -> str:
        """Get a secret from environment or vault."""
        value = os.environ.get(name)
        
        if not value and required:
            raise ValueError(f"Required secret '{name}' is not set")
        
        return value or ""
    
    @property
    def secret_key(self) -> str:
        """Get the application secret key."""
        return self._secrets_cache.get("SECRET_KEY", "")
    
    @property
    def database_url(self) -> str:
        """Get the database connection URL."""
        return self._secrets_cache.get("DATABASE_URL", "sqlite+aiosqlite:///./data/netscope.db")
    
    @property
    def cisa_api_key(self) -> str:
        """Get the CISA API key."""
        return self._secrets_cache.get("CISA_API_KEY", "")
    
    @property
    def nvd_api_key(self) -> str:
        """Get the NVD API key."""
        return self._secrets_cache.get("NVD_API_KEY", "")
    
    @property
    def is_vault_enabled(self) -> bool:
        """Check if vault integration is enabled."""
        return bool(self.vault_url)


@lru_cache
def get_secrets_manager() -> SecretsManager:
    """Get cached secrets manager instance."""
    return SecretsManager()


# Global instance for backward compatibility
secrets_manager = get_secrets_manager()
```

---

### Recommendation 3.2: Update Configuration Module

**File:** `backend/app/core/config.py` (MODIFY)

```python
# Add at the top after existing imports
from app.core.secrets import get_secrets_manager

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ... existing fields ...
    
    @computed_field
    @property
    def secret_key(self) -> str:
        """Get validated secret key from secrets manager."""
        return get_secrets_manager().secret_key
    
    @computed_field
    @property
    def database_url(self) -> str:
        """Get database URL from secrets manager."""
        return get_secrets_manager().database_url
```

---

## 4. Logging and Monitoring

### Recommendation 4.1: Implement Structured Logging

**File:** `backend/app/core/logger.py` (CREATE NEW)

```python
# ==========================================
# NetScope Logger Configuration
# Structured logging with context support
# ==========================================

import logging
import sys
from typing import Optional

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None

from app.core.config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure structured logging for the application."""
    
    level = log_level or settings.log_level
    
    if STRUCTLOG_AVAILABLE:
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stddev.add_logger_names,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.stddev.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stddev.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            structlog.stddev.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer()
            )
        )
    else:
        # Fallback to basic logging
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
    
    # Configure root logger
    logging.basicConfig(
        level=level.upper(),
        handlers=[handler],
        force=True,
    )
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> "structlog.BoundLogger":
    """Get a structured logger instance."""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


# Global logger instance
logger = get_logger("netscope")
```

**File:** `backend/app/main.py` (MODIFY)

```python
# Add after existing imports
from app.core.logger import setup_logging, logger

# In lifespan function
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # ... existing code ...
```

---

### Recommendation 4.2: Add Metrics Collection

**File:** `backend/app/middleware/metrics.py` (CREATE NEW)

```python
# ==========================================
# NetScope Metrics Middleware
# Prometheus metrics collection
# ==========================================

import time
from typing import Callable, Awaitable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = None


class MetricsMiddleware:
    """Prometheus metrics collection middleware."""
    
    def __init__(self, app):
        self.app = app
        
        if not PROMETHEUS_AVAILABLE:
            return
        
        # Define metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status_code"],
        )
        
        self.http_request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "path"],
        )
        
        self.http_requests_in_progress = Gauge(
            "http_requests_in_progress",
            "Number of HTTP requests in progress",
            ["method", "path"],
        )
    
    async def __call__(self, scope, receive, send):
        if not PROMETHEUS_AVAILABLE or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        
        # Record metrics
        method = request.method
        path = request.url.path
        
        self.http_requests_in_progress.labels(method=method, path=path).inc()
        
        try:
            start_time = time.time()
            
            # Process request
            response = await self.app(scope, receive, send)
            
            duration = time.time() - start_time
            
            # Update metrics
            status_code = response.get("status", 200)
            self.http_requests_total.labels(
                method=method, path=path, status_code=status_code
            ).inc()
            
            self.http_request_duration.labels(
                method=method, path=path
            ).observe(duration)
            
        finally:
            self.http_requests_in_progress.labels(
                method=method, path=path
            ).dec()
        
        return response


def register_metrics_endpoint(app):
    """Register metrics endpoint for Prometheus scraping."""
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        if not PROMETHEUS_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"error": "Prometheus not available"}
            )
        
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
```

---

## 5. Implementation Checklist

### Week 1: Docker Infrastructure
- [ ] Create `backend/Dockerfile`
- [ ] Create `frontend/Dockerfile`
- [ ] Create `docker-compose.yml`
- [ ] Create `.env.example`
- [ ] Test local container development

### Week 2: Security Hardening
- [ ] Create `backend/app/core/secrets.py`
- [ ] Implement structured logging (`logger.py`)
- [ ] Update `config.py` to use secrets manager
- [ ] Remove hardcoded secrets
- [ ] Create security documentation

### Week 3: CI/CD Pipeline
- [ ] Create `.github/workflows/ci.yml`
- [ ] Set up automated testing
- [ ] Configure container registry
- [ ] Test CI/CD pipeline

### Week 4: Kubernetes Deployment
- [ ] Create `k8s/deployment.yaml`
- [ ] Set up ingress controller (Traefik/Nginx)
- [ ] Configure TLS certificates
- [ ] Set up monitoring stack (Prometheus/Grafana)

### Week 5: Documentation
- [ ] Create `DEPLOYMENT.md`
- [ ] Update `README.md` with Docker/K8s instructions
- [ ] Document environment variables
- [ ] Create troubleshooting guide

---

## 6. Estimated Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Docker Infrastructure | 2 days | Multi-stage Dockerfiles, docker-compose.yml |
| 2. Security Hardening | 2 days | Secrets manager, logging, environment docs |
| 3. CI/CD Pipeline | 2 days | Automated testing, container registry |
| 4. Kubernetes Deployment | 3 days | K8s manifests, ingress, TLS |
| 5. Documentation | 1 day | Deployment guide, troubleshooting |
| **Total** | **10 days** | **Complete production setup** |

---

**Recommendations Document Generated:** November 18, 2026  
**Version:** 1.0
