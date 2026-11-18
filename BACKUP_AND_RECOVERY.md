# NetScope Database Backup and Recovery Guide

**Date:** November 18, 2026  
**Version:** 1.0

---

## Overview

This document describes the database backup and recovery strategy for NetScope.

---

## Database Configuration

### Supported Databases

| Database | Production | Development |
|----------|------------|-------------|
| PostgreSQL | ✅ Yes | ❌ No (use SQLite) |
| SQLite | ⚠️ Limited | ✅ Yes |

### Database Connection

```yaml
# PostgreSQL (Production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/netscope

# SQLite (Development)
DATABASE_URL=sqlite+aiosqlite:///app.db
```

---

## Backup Strategy

### Full Backups (Daily)

Perform full database backups at least once per day.

#### PostgreSQL Backup Command

```bash
docker exec -t netscope-postgres \
  pg_dumpall -U netscope > backups/postgresql_$(date +%Y%m%d_%H%M%S).sql
```

#### SQLite Backup Command

```bash
docker exec netscope-backend \
  sh -c 'sqlite3 /app/app.db ".backup /app/backups/sqlite_$(date +%Y%m%d_%H%M%S).db"'
```

### Incremental Backups (Hourly)

For PostgreSQL, implement WAL archiving for point-in-time recovery.

---

## Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
POSTGRES_USER="${POSTGRES_USER:-netscope}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
if [ "${DATABASE_URL}" != *"://app.db"* ]; then
    echo "Creating PostgreSQL backup..."
    docker exec -t netscope-postgres \
        pg_dumpall -U "$POSTGRES_USER" > "$BACKUP_DIR/postgresql_${DATE}.sql"
else
    echo "Creating SQLite backup..."
    docker exec netscope-backend \
        sh -c 'sqlite3 /app/app.db ".backup /app/backups/sqlite_${DATE}.db"'
fi

# Retention: Keep backups for 30 days
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete

echo "Backup completed: ${DATE}"
```

---

## Restore Procedure

### PostgreSQL Restore

```bash
# Stop services
docker-compose down

# Restore database
cat backups/postgresql_20261118_030000.sql | docker exec -i netscope-postgres \
    psql -U netscope -d netscope

# Start services
docker-compose up -d
```

### SQLite Restore

```bash
# Stop services
docker-compose down

# Restore database
cat backups/sqlite_20261118_030000.db > /path/to/app.db

# Start services
docker-compose up -d
```

---

## Backup Verification

### Verify Backup Integrity

#### PostgreSQL

```bash
# Test backup file validity
pg_restore --list backups/postgresql_20261118_030000.sql
```

#### SQLite

```bash
# Verify database integrity
sqlite3 backups/sqlite_20261118_030000.db "PRAGMA integrity_check;"
```

### Test Restoration

Perform restoration tests monthly:

```bash
# Create test database
docker run --rm \
    -e POSTGRES_USER=netscope_test \
    -e POSTGRES_PASSWORD=test123 \
    -e POSTGRES_DB=netscope_test \
    -v $(pwd)/backups:/backups \
    postgres:15-alpine \
    bash -c 'psql -U netscope_test -d netscope_test < /backups/postgresql_20261118_030000.sql'

# Verify data restored correctly
docker exec -it netscope-test psql -U netscope_test -d netscope_test -c "SELECT COUNT(*) FROM vulnerabilities;"
```

---

## Disaster Recovery

### Recovery Time Objective (RTO)

- Target: 1 hour for full restoration
- Maximum: 4 hours with additional effort

### Recovery Point Objective (RPO)

- Target: 24 hours (daily backups)
- Extended: 1 hour with WAL archiving

### Recovery Procedures

#### Scenario 1: Database Corruption

```bash
# Stop services
docker-compose down

# Remove corrupted database volume
docker volume rm netscope_postgres_data

# Restore from latest backup
cat backups/postgresql_20261118_030000.sql | docker exec -i netscope-postgres psql -U netscope

# Start services
docker-compose up -d
```

#### Scenario 2: Complete System Failure

```bash
# On new server:
1. Install Docker and Docker Compose
2. Clone repository
3. Restore database from backup
4. Run migrations: alembic upgrade head
5. Start services
```

---

## Backup Storage

### Local Storage

- Backups stored in `/app/backups/`
- Retention: 30 days
- Minimum free space: 10 GB

### Remote Storage (Recommended)

#### AWS S3

```bash
# Upload backup to S3
aws s3 cp backups/postgresql_$(date +%Y%m%d).sql \
    s3://your-backup-bucket/netscope/
```

#### Google Cloud Storage

```bash
gsutil cp backups/postgresql_$(date +%Y%m%d).sql \
    gs://your-backup-bucket/netscope/
```

#### Azure Blob Storage

```bash
az storage blob upload \
    --account-name youraccount \
    --container-name backups \
    --name postgresql_$(date +%Y%m%d).sql \
    --file backups/postgresql_$(date +%Y%m%d).sql
```

---

## Database Migrations

### Running Migrations

```bash
# Apply pending migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision -m "description"
```

### Migration Verification

```bash
# Check migration status
docker-compose exec backend alembic current

# Show migration history
docker-compose exec backend alembic history
```

---

## Backup Schedule

### Recommended Cron Job

```bash
# Daily backup at 3:00 AM
0 3 * * * /app/scripts/backup.sh >> /var/log/backup.log 2>&1

# Weekly full backup on Sunday at 4:00 AM
0 4 * * 0 /app/scripts/backup_full.sh >> /var/log/backup.log 2>&1
```

---

## Monitoring Backups

### Alert on Backup Failure

```python
# Add to monitoring
def check_last_backup():
    last_backup = get_last_backup_file()
    if not last_backup:
        return {"status": "unhealthy", "message": "No backups found"}
    
    backup_age = get_backup_age(last_backup)
    if backup_age > 86400:  # 24 hours
        return {"status": "degraded", "message": f"Last backup {backup_age/3600:.1f} hours ago"}
    
    return {"status": "healthy", "message": f"Last backup {backup_age/60:.1f} minutes ago"}
```

---

## Checklist for Production Deployment

Before going to production:

- [ ] Automated backup script created
- [ ] Backup retention policy configured
- [ ] Remote storage configured (S3/Google Cloud/Azure)
- [ ] Restoration test performed
- [ ] Backup integrity verification implemented
- [ ] Alerting for backup failures configured
- [ ] Documentation reviewed

---

*Database Backup and Recovery Guide Generated on November 18, 2026*
