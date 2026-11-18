# NetScope Monitoring and Logging Documentation

**Date:** November 18, 2026  
**Version:** 1.0

---

## Overview

This document describes the monitoring, logging, and observability infrastructure for NetScope.

---

## Application Logging

### Log Format

NetScope uses structured JSON logs for consistent parsing and analysis.

### Log Levels

| Level | Purpose |
|-------|---------|
| DEBUG | Detailed information for debugging |
| INFO | General application events |
| WARNING | Non-critical issues |
| ERROR | Error conditions |
| CRITICAL | Critical failures |

### Log Contents

Each log entry includes:

```json
{
  "timestamp": "2026-11-18T13:45:30.123Z",
  "level": "INFO",
  "message": "Application started",
  "request_id": "req_abc123",
  "user_id": "user_456",
  "endpoint": "/api/v1/scans",
  "method": "POST",
  "status_code": 200,
  "response_time_ms": 45,
  "additional_data": {
    // Context-specific information
  }
}
```

### Sensitive Data Exclusion

The following data is NEVER logged:

- ❌ Passwords (hashed or plaintext)
- ❌ JWT tokens
- ❌ API keys
- ❌ Secret keys
- ❌ Sensitive personal information

### Structured Logging Implementation

```python
import structlog

logger = structlog.get_logger()

# Example usage
logger.info(
    "user_login",
    user_id=user.id,
    ip_address=request.client.host,
    success=True
)
```

---

## Health Endpoints

### Basic Health Check

**Endpoint:** `GET /health`

```json
{
  "status": "healthy"
}
```

**Response Codes:**
- `200 OK` - Application is healthy
- `503 Service Unavailable` - Application is unhealthy

### Extended Health Check

**Endpoint:** `GET /health/extended`

```json
{
  "overall_status": "healthy",
  "timestamp": 1731927600.123,
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "NVD": {
      "status": "healthy",
      "response_code": 200
    },
    "CISA KEV": {
      "status": "healthy",
      "response_code": 200
    },
    "nmap": {
      "status": "healthy"
    }
  }
}
```

---

## Application Metrics

### Prometheus Metrics (Optional)

When Prometheus integration is enabled, the following metrics are exposed:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `http_requests_in_progress` | Gauge | In-progress requests |
| `database_connections` | Gauge | Active database connections |
| `jwts_validated_total` | Counter | JWT tokens validated |
| `api_keys_validated_total` | Counter | API keys validated |
| `cve_intel_requests_total` | Counter | CVE intelligence requests |

### Metrics Endpoints

- **Prometheus:** `/metrics` (when enabled)
- **Metrics health:** `/health/metrics`

---

## Docker Monitoring

### Container Health Checks

All containers include built-in health checks:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Docker Logs

```bash
# View backend logs
docker-compose logs -f backend

# View frontend logs
docker-compose logs -f frontend

# View all logs
docker-compose logs -f
```

---

## Logging Configuration

### Development

```bash
# Console logging with colors
uvicorn app.main:app --reload
```

### Production

```bash
# JSON structured logging to file
uvicorn app.main:app --log-config logging.yml
```

### Logging Configuration File

Example `logging.yml`:

```yaml
version: 1
disable_existing_loggers: False

formatters:
  standard:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  json:
    "()": "structlog.stdlib.ProcessorFormatter"
    processor: structlog.processors.JSONRenderer

handlers:
  console:
    class: logging.StreamHandler
    formatter: standard
  file:
    class: logging.FileHandler
    filename: /var/log/netscope/app.log
    formatter: json

loggers:
  app:
    level: INFO
    handlers: [console, file]
  uvicorn:
    level: WARNING
    handlers: [console]

root:
  level: INFO
  handlers: [console]
```

---

## Alerting

### Recommended Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| High error rate | >1% of requests in 5 min | Notify ops team |
| Database unavailable | Health check fails | PagerDuty alert |
| High CPU usage | >80% for 10 min | Notify ops team |
| Missing secret keys | Startup failure | Immediate notification |
| Rate limit exceeded | >1000 req/min from single IP | Block IP |

---

## Observability Best Practices

### Request Correlation IDs

All requests include a `X-Request-ID` header:

```python
# Generate unique request ID
request_id = f"req_{uuid.uuid4().hex[:12]}"
response.headers["X-Request-ID"] = request_id
```

### Tracing (Optional)

For distributed tracing, integrate with:

- Jaeger
- OpenTelemetry
- Datadog APM

### Log Aggregation

For production, use:

- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki + Prometheus
- CloudWatch Logs (AWS)
- Stackdriver Logging (GCP)

---

## Monitoring Tools

### Free/Open Source

1. **Prometheus + Grafana**
   - Metrics collection and visualization
   - Alerting rules

2. **Jaeger**
   - Distributed tracing
   - Request latency analysis

3. **ELK Stack**
   - Log aggregation and search
   - Advanced querying

### Cloud Providers

1. **AWS CloudWatch**
   - Metrics, logs, alarms
   - Integration with ECS/EKS

2. **Google Cloud Operations**
   - Logging, monitoring, tracing
   - Integration with GKE

3. **Azure Monitor**
   - Application Insights
   - Container monitoring

---

## Production Checklist

Before deploying to production, ensure:

- [ ] Structured JSON logging configured
- [ ] Health check endpoints accessible
- [ ] Metrics endpoint (if using Prometheus) enabled
- [ ] Log aggregation configured
- [ ] Alerting rules defined
- [ ] Docker health checks defined
- [ ] Security headers configured in nginx

---

## Troubleshooting

### Common Issues

#### Container unhealthy
```bash
docker-compose ps
docker-compose logs backend
```

#### Database connection failed
```bash
# Check database container
docker-compose ps postgres

# Test database connectivity
docker exec -it netscope-postgres psql -U netscope -c "SELECT 1"
```

#### High error rate
```bash
# Check logs for errors
docker-compose logs --tail=100 backend | grep ERROR

# View detailed health check
curl http://localhost:8000/health/extended
```

---

*Monitoring and Logging Documentation Generated on November 18, 2026*
