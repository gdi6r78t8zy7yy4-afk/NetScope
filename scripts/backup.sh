#!/bin/bash

# NetScope Database Backup Script
# Creates a full database backup with optional point-in-time recovery support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="netscope_backup_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Load environment variables
if [ -f "${SCRIPT_DIR}/../backend/.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../backend/.env" | xargs)
fi

# Default values if not set
POSTGRES_USER="${POSTGRES_USER:-netscope}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me-in-production}"
POSTGRES_DB="${POSTGRES_DB:-netscope}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Check for required tools
check_requirements() {
    local missing=0
    
    if ! command -v psql &> /dev/null; then
        log "ERROR: psql command not found. Please install PostgreSQL client."
        missing=1
    fi
    
    if ! command -v gzip &> /dev/null; then
        log "ERROR: gzip command not found."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

# Create backup
create_backup() {
    log "Starting database backup..."
    
    # Set PostgreSQL password for non-interactive authentication
    export PGPASSWORD="${POSTGRES_PASSWORD}"
    
    # Create backup with pg_dump
    log "Dumping database: ${POSTGRES_DB} from host: ${POSTGRES_HOST}"
    
    # Execute backup with compression
    pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        2>"${LOG_FILE}" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"
    
    # Reset password
    unset PGPASSWORD
    
    log "Backup completed: ${BACKUP_DIR}/${BACKUP_FILE}"
    
    # Create backup metadata file
    cat > "${BACKUP_DIR}/backup_metadata_${TIMESTAMP}.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "database": "${POSTGRES_DB}",
  "host": "${POSTGRES_HOST}",
  "user": "${POSTGRES_USER}",
  "backup_file": "${BACKUP_FILE}",
  "size_bytes": $(stat -f%z "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null),
  "checksum": "$(sha256sum "${BACKUP_DIR}/${BACKUP_FILE}" | cut -d' ' -f1)"
}
EOF
    
    log "Metadata saved: ${BACKUP_DIR}/backup_metadata_${TIMESTAMP}.json"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
        log "ERROR: Backup file not found: ${BACKUP_DIR}/${BACKUP_FILE}"
        exit 1
    fi
    
    # Check file size
    local size=$(stat -f%z "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null)
    if [ "$size" -lt 100 ]; then
        log "ERROR: Backup file too small (${size} bytes)"
        exit 1
    fi
    
    # Verify gzip integrity
    if ! gzip -t "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null; then
        log "ERROR: Backup file is corrupted"
        exit 1
    fi
    
    # Check checksum if metadata exists
    local meta_file="${BACKUP_DIR}/backup_metadata_${TIMESTAMP}.json"
    if [ -f "$meta_file" ]; then
        local stored_checksum=$(grep '"checksum"' "$meta_file" | cut -d'"' -f4)
        local actual_checksum=$(sha256sum "${BACKUP_DIR}/${BACKUP_FILE}" | cut -d' ' -f1)
        
        if [ "$stored_checksum" != "$actual_checksum" ]; then
            log "WARNING: Checksum mismatch (backup may have been modified)"
        else
            log "Checksum verification passed"
        fi
    fi
    
    log "Backup verification completed successfully"
}

# List backups
list_backups() {
    log "Available backups:"
    
    if [ -d "${BACKUP_DIR}" ]; then
        ls -lh "${BACKUP_DIR}/"*.sql.gz 2>/dev/null || echo "No backups found"
        ls -lh "${BACKUP_DIR}/"backup_metadata_*.json 2>/dev/null || echo "No metadata files found"
    else
        log "Backup directory does not exist: ${BACKUP_DIR}"
        exit 1
    fi
}

# Restore from backup (use with caution!)
restore_backup() {
    local backup_file="${1}"
    
    if [ -z "$backup_file" ]; then
        log "ERROR: Please specify a backup file to restore"
        list_backups
        exit 1
    fi
    
    if [ ! -f "${BACKUP_DIR}/${backup_file}" ]; then
        log "ERROR: Backup file not found: ${BACKUP_DIR}/${backup_file}"
        exit 1
    fi
    
    log "WARNING: This will overwrite the current database!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log "Restore cancelled"
        exit 0
    fi
    
    export PGPASSWORD="${POSTGRES_PASSWORD}"
    
    log "Restoring from backup: ${backup_file}"
    
    # Drop and recreate database
    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"
    
    # Restore from backup
    zcat "${BACKUP_DIR}/${backup_file}" | psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" 2>"${LOG_FILE}"
    
    unset PGPASSWORD
    
    log "Restore completed"
}

# Cleanup old backups
cleanup_old_backups() {
    local days_to_keep="${1:-7}"
    
    log "Cleaning up backups older than ${days_to_keep} days..."
    
    find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${days_to_keep} -delete
    find "${BACKUP_DIR}" -name "backup_metadata_*.json" -mtime +${days_to_keep} -delete
    find "${BACKUP_DIR}" -name "backup_*.log" -mtime +${days_to_keep} -delete
    
    log "Cleanup completed"
}

# Main
case "${1:-backup}" in
    backup)
        check_requirements
        create_backup
        verify_backup
        ;;
    verify)
        verify_backup
        ;;
    list)
        list_backups
        ;;
    restore)
        shift
        restore_backup "$@"
        ;;
    cleanup)
        shift
        cleanup_old_backups "${1:-7}"
        ;;
    *)
        echo "Usage: $0 {backup|verify|list|restore <file>|cleanup [days]}"
        echo ""
        echo "Commands:"
        echo "  backup    Create a new database backup"
        echo "  verify    Verify the integrity of the latest backup"
        echo "  list      List all available backups"
        echo "  restore   Restore from a specific backup file"
        echo "  cleanup   Remove backups older than specified days (default: 7)"
        exit 1
        ;;
esac
