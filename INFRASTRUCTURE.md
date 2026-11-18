# NetScope Infrastructure Guide

**Last Updated:** November 18, 2026  
**Version:** 2.0

---

## Overview

This document describes the complete infrastructure setup for NetScope, including Docker containerization, Kubernetes deployment, CI/CD pipelines, and security best practices.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Local Development with Docker](#local-development-with-docker)
4. [Production Deployment with Kubernetes](#production-deployment-with-kubernetes)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Security Best Practices](#security-best-practices)
7. [Monitoring and Logging](#monitoring-and-logging)

---

## Quick Start

### Prerequisites
- Docker 24.0+
- Kubernetes 1.28+ (optional, for production)
- Helm 3.10+ (optional)
- GitHub CLI (for CI/CD)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/netscope.git
cd netscope

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
open http://localhost:3000
```

### Production Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/deployment.yaml

# Check deployment status
kubectl rollout status deployment/netscope-backend
kubectl rollout status deployment/netscope-frontend

# Access the application (configure DNS to point to ingress IP)
open http://netscope.example.com
```

---

## Architecture

### Current State (Ad-hoc)

The original application runs directly on the host system:

```
┌──────────────┐    ┌──────────────┐    ┌───────────────┐
│   Tauri App  │    │  Frontend    │    │   Backend     │
│  (Desktop)   │    │  React/TS    │    │ FastAPI       │
└──────────────┘    └──────────────┘    └───────┬────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  SQLite DB   │
                                          │ (Local Only) │
                                          └──────────────┘
```

### Recommended Production Architecture

The recommended production setup uses containerization with optional Kubernetes orchestration:

```
┌──────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                          Ingress                       │    │
│  └──────────────┬───────────────────────────────────────┘    │
│                 │                                             │
│         ┌───────▼─────────┐      ┌────────────────────┐      │
│         │  Frontend       │      │     Backend        │      │
│         │  (Port 3000)    │      │   (Port 8000)      │      │
│         └─────────────────┘      └────────┬───────────┘      │
│                                             │                 │
│                                             ▼                 │
│                                      ┌─────────────┐          │
│                                      │  PostgreSQL │          │
│                                      │  (Port 5432)│          │
│                                      └─────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

### Docker Compose Architecture

For simpler deployments without Kubernetes:

```
┌──────────────────┐        ┌──────────────────┐
│   Frontend       │        │   Backend        │
│  (Port 3000)     │───────▶│  (Port 8000)     │
│  Nginx/Node      │ HTTP   │  FastAPI/Uvicorn │
└──────────────────┘        └───────┬──────────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │  PostgreSQL  │
                             │  (Port 5432) │
                             └──────────────┘
```

---

## Local Development with Docker

### Prerequisites
- Docker 24.0 or higher
- Docker Compose v2

### Setup

1. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your configuration:**
   ```bash
   # Core Settings
   SECRET_KEY=your-secure-secret-key-here
   DEBUG=true
   LOG_LEVEL=INFO

   # Backend Server
   BACKEND_HOST=localhost
   BACKEND_PORT=8000

   # Database (Development uses SQLite)
   DATABASE_URL=sqlite+aiosqlite:///./data/netscope.db

   # Scanning
   DEFAULT_RATE_LIMIT=medium
   MAX_CONCURRENT_HOSTS=5
   SCAN_TIMEOUT_SECONDS=3600

   # Security
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

3. **Build and start services:**
   ```bash
   # Build all images
   docker-compose build

   # Start all services in detached mode
   docker-compose up -d
   ```

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Execute commands in running container
docker-compose exec backend bash
docker-compose exec frontend sh

# Check service health
docker-compose ps

# Stop and remove volumes (database data)
docker-compose down -v
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Web UI (Nginx) |
| Backend | 8000 | FastAPI API |
| Database | 5432 | PostgreSQL |

### Accessing Services

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Production Deployment with Kubernetes

### Prerequisites
- Kubernetes cluster (EKS, GKE, AKS, or local like kind)
- kubectl configured
- Helm 3.10+ (optional, for Helm chart deployment)
- DNS domain (e.g., netscope.example.com)

### Deployment Steps

1. **Update Kubernetes manifest:**
   Edit `k8s/deployment.yaml` and replace placeholders:
   ```yaml
   # Replace in k8s/deployment.yaml
   - name: image: ghcr.io/your-org/netscope-backend:latest
   - secretName: netscope-tls  # Update with your TLS secret name
   ```

2. **Create secrets:**
   ```bash
   # Create TLS secret (for HTTPS)
   kubectl create secret tls netscope-tls \
     --cert=path/to/tls.crt \
     --key=path/to/tls.key

   # Create database password secret
   kubectl create secret generic netscope-secrets \
     --from-literal=secret-key=$(openssl rand -base64 32) \
     --from-literal=database-url="postgresql://user:password@host:5432/netscope"
   ```

3. **Apply deployment:**
   ```bash
   # Apply all manifests
   kubectl apply -f k8s/deployment.yaml

   # Check deployment status
   kubectl rollout status deployment/netscope-backend
   kubectl rollout status deployment/netscope-frontend

   # Check pod status
   kubectl get pods -l app=netscope

   # View logs
   kubectl logs -l app=netscope-backend -f
   ```

4. **Configure Ingress:**
   ```bash
   # Install Traefik (if not already installed)
   helm install traefik traefik/traefik

   # Or use Nginx Ingress
   helm install nginx-ingress ingress-nginx/ingress-nginx
   ```

### Scaling

```bash
# Scale backend horizontally
kubectl scale deployment/netscope-backend --replicas=5

# Scale frontend horizontally
kubectl scale deployment/netscope-frontend --replicas=3

# Check horizontal pod autoscaler
kubectl get hpa
```

### Rolling Updates

```bash
# Trigger rolling update (when image tag changes)
kubectl rollout restart deployment/netscope-backend

# Check rollout status
kubectl rollout status deployment/netscope-backend

# Rollback if needed
kubectl rollout undo deployment/netscope-backend
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline is configured in `.github/workflows/ci.yml` and includes:

1. **Backend Testing** - Python tests with coverage
2. **Frontend Testing** - TypeScript compilation and tests
3. **Security Scanning** - Trivy vulnerability scanning
4. **Build & Push** - Build and push Docker images to GitHub Container Registry
5. **Deployment** - Deploy to Kubernetes cluster

### Setup Steps

1. **Create GitHub secrets:**
   ```bash
   # Set up repository secrets in GitHub UI
   GHCR_TOKEN=your-github-personal-access-token
   KUBE_CONFIG=base64-encoded-kubeconfig-for-cluster
   ```

2. **Configure cluster access:**
   ```bash
   # For Kubernetes deployment
   kubectl create serviceaccount github-actions \
     --namespace default

   kubectl create clusterrolebinding github-actions \
     --clusterrole=cluster-admin \
     --serviceaccount=default:github-actions
   ```

3. **Trigger CI/CD:**
   ```bash
   # Push to main branch
   git push origin main

   # Or create a pull request
   gh pr create --title "Update application" --body "Description"
   ```

### Pipeline Stages

| Stage | Description |
|-------|-------------|
| test-backend | Run Python tests with coverage |
| test-frontend | Run TypeScript compilation and tests |
| security-scan | Scan for vulnerabilities with Trivy |
| build-and-push | Build and push Docker images to GHCR |
| deploy | Deploy to Kubernetes cluster |

---

## Security Best Practices

### Environment Variables

**Never commit secrets to version control.**

```bash
# Add .env to .gitignore
echo ".env" >> .gitignore

# Use .env.example as template
cp .env.example .env
```

### Secrets Management

For production, use a secrets manager:

#### HashiCorp Vault Integration
```bash
# Set VAULT_URL in environment
export VAULT_URL=https://vault.example.com

# Generate secrets via Vault API
vault kv put secret/netscope \
  SECRET_KEY=$(openssl rand -base64 32) \
  DATABASE_URL=postgresql://user:pass@host/db
```

#### Kubernetes Secrets
```bash
# Create secrets for production
kubectl create secret generic netscope-secrets \
  --from-literal=secret-key=$(openssl rand -base64 32) \
  --from-literal=database-url="postgresql://user:pass@host/db"
```

### Network Security

1. **Use PodSecurityPolicy** (or Pod Security Standards in Kubernetes 1.23+)
2. **Enable network policies** to restrict pod-to-pod communication
3. **Use TLS for all external traffic**
4. **Disable CORS in production** and specify exact origins

### Container Security

```bash
# Scan container images for vulnerabilities
trivy image ghcr.io/your-org/netscope-backend:latest

# Run with read-only filesystem
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
```

---

## Monitoring and Logging

### Structured Logging

The application uses `structlog` for structured logging.

#### Log Output Example
```json
{
  "timestamp": "2026-11-18T10:30:45.123Z",
  "level": "INFO",
  "logger": "netscope",
  "request_id": "req-abc123",
  "message": "Application started successfully"
}
```

#### Enable Debug Logging
```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
```

### Prometheus Metrics

The application exposes metrics at `/metrics` endpoint.

#### Available Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, path, status |
| `http_request_duration_seconds` | Histogram | Request duration distribution |
| `http_requests_in_progress` | Gauge | Active requests count |

#### Configure Prometheus
```yaml
scrape_configs:
  - job_name: 'netscope-backend'
    metrics_path: /metrics
    static_configs:
      - targets: ['netscope-backend-service:8000']
```

### Grafana Dashboard

Import the dashboard JSON for monitoring NetScope metrics (not provided in this repository).

---

## Troubleshooting

### Common Issues

#### 1. Backend won't start
```bash
# Check logs
docker-compose logs backend

# Verify environment variables
docker-compose exec backend env | grep DATABASE_URL
```

#### 2. Frontend can't connect to backend
```bash
# Check network connectivity
docker-compose exec frontend ping backend

# Verify backend port is exposed
docker-compose ps
```

#### 3. Kubernetes pod CrashLoopBackOff
```bash
# Check logs
kubectl logs <pod-name> --previous

# Describe pod for events
kubectl describe pod <pod-name>

# Check health probes
kubectl get events --sort-by='.lastTimestamp'
```

#### 4. Database connection failed
```bash
# Verify database is running
docker-compose ps db

# Test database connection
docker-compose exec db psql -U postgres -c "SELECT 1"
```

### Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | Basic health check |
| `/health/extended` | Detailed status with dependencies |

---

## Performance Optimization

### Backend Optimization
```dockerfile
# Use multi-stage builds
# Install only required packages
# Cache dependencies separately from code
```

### Frontend Optimization
```nginx
# Enable gzip compression
gzip on;

# Set aggressive caching
location ~* \.(js|css)$ {
    expires 1y;
}
```

### Database Optimization
```yaml
# Configure PostgreSQL resources
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

---

## Cleanup

### Docker
```bash
# Stop and remove containers
docker-compose down

# Remove unused images
docker image prune -a

# Remove volumes
docker volume prune
```

### Kubernetes
```bash
# Delete deployment
kubectl delete -f k8s/deployment.yaml

# Clean up secrets
kubectl delete secret netscope-secrets
```

---

## Support

For issues and questions:
1. Check the logs: `docker-compose logs` or `kubectl logs`
2. Review this documentation
3. Open a GitHub issue

---

**Document Version:** 1.0  
**Last Updated:** November 18, 2026
