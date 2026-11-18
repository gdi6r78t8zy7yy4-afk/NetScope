# NetScope Deployment Guide

## Overview

This guide covers secure deployment practices for NetScope, including secrets management and environment configuration.

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (for version control)

## Security Checklist

Before deploying to production:

- [ ] Generate secure random keys for `SECRET_KEY` and `API_KEY`
- [ ] Use environment variables or a secrets manager
- [ ] Never commit `.env` files to version control
- [ ] Set `DEBUG=false` in production
- [ ] Configure CORS origins explicitly
- [ ] Enable HTTPS for all endpoints
- [ ] Set up log rotation and monitoring

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret for JWT tokens and encryption | `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `API_KEY` | API key for external service authentication | Same generation as SECRET_KEY |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment name | `development` |
| `DEBUG` | Debug mode (false in prod) | `false` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DATABASE_URL` | Database connection string | SQLite local |
| `BACKEND_HOST` | Server host | `localhost` |
| `BACKEND_PORT` | Server port | `8000` |
| `CISA_API_KEY` | CISA vulnerability API key | (empty) |
| `NVD_API_KEY` | NVD vulnerability API key | (empty) |
| `ALLOWED_ORIGINS` | CORS allowed origins | (comma-separated list) |

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd networking
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c 'import secrets; print(secrets.token_hex(32))'

# Generate API_KEY
python -c 'import secrets; print(secrets.token_hex(32))'

# Add to .env
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
echo "API_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
```

### 4. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload

# Production mode
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Kubernetes

See `kubernetes/` directory for Helm chart and manifests.

## Secrets Management

### Option 1: Environment Variables (Simple)

```bash
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
export API_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
export DATABASE_URL=postgresql://...
```

### Option 2: HashiCorp Vault

```bash
# Install vault CLI
brew install vault

# Login and retrieve secrets
vault login
vault read secret/data/netscope
```

### Option 3: AWS Secrets Manager

```bash
aws secretsmanager get-secret-value \
    --secret-id netscope/secrets \
    --query SecretString \
    --output text
```

### Option 4: Docker Secrets

```bash
echo "my-secret-key" | docker secret create secret_key -
```

## Security Best Practices

### 1. Key Rotation

Rotate secrets regularly (every 90 days recommended):

```bash
# Generate new keys
python -c 'import secrets; print(secrets.token_hex(32))'

# Update in secrets manager
# Deploy new configuration
# Restart services
```

### 2. Least Privilege

- Run application as non-root user
- Grant minimum required database permissions
- Use separate API keys for different services

### 3. Encryption at Rest

- Enable database encryption
- Use HTTPS/TLS for all connections
- Encrypt backup files

### 4. Monitoring and Alerts

- Log all authentication failures
- Alert on invalid API keys
- Monitor for unusual access patterns

## Troubleshooting

### Application Won't Start

Error: `SECRET_KEY environment variable must be set`

**Solution:** Create `.env` file with SECRET_KEY:

```bash
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env
```

### API Key Validation Fails

Error: `Invalid API key`

**Solution:** Ensure API_KEY is set in environment:

```bash
export API_KEY="your-generated-api-key"
```

### Database Connection Fails

**Solution:** Verify DATABASE_URL format:

```bash
# SQLite
DATABASE_URL=sqlite+aiosqlite:///./data/netscope.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: pytest app/tests/
      
      - name: Deploy
        env:
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          # Deployment commands
```

### GitLab CI Example

```yaml
deploy:
  stage: deploy
  environment:
    name: production
  script:
    - export SECRET_KEY="${SECRET_KEY}"
    - export API_KEY="${API_KEY}"
    - pytest app/tests/
    - ./deploy.sh
  only:
    - main
```

## Security Incident Response

### Suspected Key Compromise

1. **Immediately** rotate the compromised key
2. Revoke all active tokens/sessions
3. Review logs for unauthorized access
4. Update all stored credentials
5. Notify security team

### Failed Authentication

Monitor for patterns indicating attack:
- Multiple failed login attempts
- Invalid API keys from same IP
- Brute force attempts

## Support

For security issues, contact: security@netscope.local

For general issues, open a GitHub issue.
