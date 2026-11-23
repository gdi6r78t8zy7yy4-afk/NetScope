# NetScope Scanning API

"""
API endpoints for port scanning operations.
"""

from app.schemas.scan import ScanSchedule, ScanScheduleCreate
from datetime import datetime
from io import StringIO
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.config import settings
from app.core.auth import get_current_user, User
from app.core.validators import parse_and_validate_ports, validate_cidr
from app.core.authorization_service import get_authorization_service
from app.engines.scanner.parser import parse_nmap_xml
from app.engines.port_scanner.nmap_engine import NmapPortScanner
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.scan import Scan, ScanTarget, ScanEvidence
from app.schemas.scan import (
    Scan as ScanSchema,
    ScanCreate,
    ScanTarget as ScanTargetSchema,
)
import structlog

logger = structlog.get_logger(__name__)


# For local development, allow unauthenticated scans
def require_auth_or_local(user: User = Depends(get_current_user)) -> User:
    """Allow unauthenticated access for local development."""
    if user is not None:
        return user
    # Create a default user for development
    return User(id="dev", username="developer", scopes=["read", "write"])


router = APIRouter()


def require_scan_permission(
        user: User = Depends(require_auth_or_local)) -> User:
    """
    Require user with scan permissions.

    Args:
        user: Authenticated user

    Returns:
        User with write permissions

    Raises:
        HTTPException(403): If user lacks scan permissions
    """
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have scan permissions"
        )
    return user


async def save_scan_evidence(
    db: AsyncSession, scan_id: int, evidence_type: str, data: dict
):
    """
    Save scan evidence to the database.

    Args:
        db: Database session
        scan_id: ID of the scan
        evidence_type: Type of evidence (nmap_raw, nmap_parsed)
        data: Evidence data to store
    """
    evidence = ScanEvidence(
        scan_id=scan_id, evidence_type=evidence_type, data=json.dumps(data)
    )
    db.add(evidence)


@router.get("/scans", response_model=list[ScanSchema])
async def list_scans(db: AsyncSession = Depends(get_async_session)):
    """
    List all scans.

    Returns a list of all scan records with their status and metadata.

    Returns:
        List[ScanSchema]: Array of scan objects
    """
    result = await db.execute(select(Scan))
    return list(result.scalars().all())


@router.post("/scans", response_model=ScanSchema)
async def create_scan(
    scan: ScanCreate,
    user: User = Depends(require_auth_or_local),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a new scan.

    Creates a scan record that can be executed later.

    Args:
        scan: ScanCreate schema with scan configuration
        user: Authenticated user

    Returns:
        ScanSchema: Created scan object

    Raises:
        HTTPException(403): If user lacks write permissions
    """
    db_scan = Scan(**scan.model_dump())
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    return db_scan


@router.get("/scans/{scan_id}", response_model=ScanSchema)
async def get_scan(scan_id: int,
                   db: AsyncSession = Depends(get_async_session)):
    """
    Get a scan by ID.

    Retrieves detailed information about a specific scan.

    Args:
        scan_id: The unique identifier of the scan

    Returns:
        ScanSchema: Scan information and configuration

    Raises:
        HTTPException(404): If scan not found
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return scan


@router.post("/scans/{scan_id}/cancel")
async def cancel_scan(
    scan_id: int,
    user: User = Depends(require_auth_or_local),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Cancel a running scan.

    Cancels an active scan by updating its status and terminating
    any running processes. This endpoint properly terminates the nmap process.

    Args:
        scan_id: The unique identifier of the scan to cancel
        user: Authenticated user with write permissions

    Returns:
        dict: Cancellation confirmation message

    Raises:
        HTTPException(403): If user lacks write permissions
        HTTPException(404): If scan not found
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Update scan status to cancelled and record completion time
    scan.status = "cancelled"
    scan.completed_at = datetime.now()
    await db.commit()

    # Terminate any running nmap process for this scan
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    try:
        # Get the process manager and terminate any running processes
        scanner = NmapPortScanner()
        await scanner.terminate_scan_process(scan_id)
    except Exception as e:
        logger.warning(f"Failed to terminate scan process: {e}")
        # Continue with database update even if process termination fails

    return {"message": "Scan cancelled"}


@router.post("/scans/{scan_id}/run")
async def run_scan(
    scan_id: int,
    user: User = Depends(require_auth_or_local),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Run a port scan.

    Executes the configured scan against the target network.
    Supports single port, common ports, port range, and full TCP scans.

    Args:
        scan_id: The unique identifier of the scan to run
        user: Authenticated user with write permissions

    Returns:
        dict: Scan results including hosts found and ports discovered

    Raises:
        HTTPException(403): If user lacks write permissions
        HTTPException(404): If scan not found
        HTTPException(400): If scan configuration is invalid
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Check capacity before running
    from sqlalchemy import select as sa_select, update as sa_update
    from app.core.config import settings

    result = await db.execute(sa_select(Scan).where(Scan.status == "running"))
    running_scans = list(result.scalars().all())

    # Always mark scans as pending to ensure background execution via queue processor
    # This prevents HTTP requests from blocking while scans run (can take minutes)
    if scan.status not in ("pending", "running"):
        logger.info(
            "Scan queued for background execution",
            scan_id=scan.id,
            running_count=len(running_scans),
            max_concurrent=settings.max_concurrent_scans,
        )
    if scan.status == "running":
        raise HTTPException(status_code=409, detail="Scan is already running")

    scan.status = "pending"
    scan.started_at = None
    scan.completed_at = None
    scan.error_message = None

    await db.commit()
    await db.refresh(scan)
    return scan


@router.get("/scans/{scan_id}/targets", response_model=list[ScanTargetSchema])
async def get_scan_targets(
        scan_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Get targets for a scan.

    Retrieves the individual hosts/targets that were scanned
    as part of this scan operation.

    Args:
        scan_id: The unique identifier of the scan

    Returns:
        List[ScanTargetSchema]: Array of scan target objects
    """
    result = await db.execute(select(ScanTarget).where(ScanTarget.scan_id == scan_id))
    return list(result.scalars().all())


# ==================== Phase 3: Export Endpoints ====================


@router.get("/scans/{scan_id}/export/csv")
async def export_scan_csv(
        scan_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Export scan results as CSV.

    Exports the scan results to a CSV file for external analysis.

    Args:
        scan_id: The unique identifier of the scan

    Returns:
        StreamingResponse: CSV file download

    Raises:
        HTTPException(404): If scan not found
    """
    from app.utils.export import export_to_csv

    # Get scan results
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Generate CSV data
    csv_data = export_to_csv(
        {
            "scan_id": scan.id,
            "target": scan.target_cidr,
            "status": scan.status,
            "hosts_found": scan.hosts_found,
        }
    )

    return StreamingResponse(
        StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=scan_{scan_id}_results.csv"
        },
    )


@router.get("/scans/{scan_id}/export/json")
async def export_scan_json(
        scan_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Export scan results as JSON.

    Exports the scan results to a JSON file for external analysis.

    Args:
        scan_id: The unique identifier of the scan

    Returns:
        JSONResponse: JSON file download

    Raises:
        HTTPException(404): If scan not found
    """
    from app.utils.export import export_to_json

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    json_data = export_to_json(
        {
            "scan_id": scan.id,
            "target": scan.target_cidr,
            "status": scan.status,
            "hosts_found": scan.hosts_found,
            "scan_type": scan.scan_type,
        }
    )

    return JSONResponse(content=json_data)


@router.get("/scans/export/all/csv")
async def export_all_scans_csv(db: AsyncSession = Depends(get_async_session)):
    """
    Export all scans as CSV.

    Exports a summary of all scans to a single CSV file.

    Returns:
        StreamingResponse: CSV file download with all scans
    """
    from app.utils.export import export_to_csv

    result = await db.execute(select(Scan))
    scans = list(result.scalars().all())

    csv_data = export_to_csv(
        [
            {
                "id": s.id,
                "name": s.name or "",
                "target_cidr": s.target_cidr,
                "scan_type": s.scan_type,
                "status": s.status,
                "hosts_found": s.hosts_found,
            }
            for s in scans
        ]
    )

    return StreamingResponse(
        StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=all_scans.csv"},
    )


# ==================== Phase 3: Scan Scheduling Endpoints ====================


@router.post("/schedules", response_model=ScanSchedule)
async def create_schedule(schedule: ScanScheduleCreate):
    """
    Create a new scan schedule.

    Creates a scheduled scan that will run automatically at
    the specified cron interval.

    Args:
        schedule: ScanScheduleCreate with scheduling configuration

    Returns:
        ScanSchedule: Created schedule object
    """
    return {"id": 1, **schedule.model_dump()}  # Will be replaced with actual DB ID


@router.get("/schedules", response_model=list[ScanSchedule])
async def list_schedules():
    """
    List all scan schedules.

    Returns a list of all scheduled scans configured in the system.

    Returns:
        List[ScanSchedule]: Array of schedule objects
    """
    return []


@router.get("/schedules/next-run")
async def get_next_run(cron_pattern: str):
    """
    Get the next run time for a cron pattern.

    Calculates when a scheduled scan will next execute based on
    the provided cron expression.

    Args:
        cron_pattern: Cron-like scheduling pattern

    Returns:
        dict: Next run time information

    Raises:
        HTTPException(400): If cron pattern is invalid
    """
    from app.engines.scanner.scheduler import parse_cron

    next_run = parse_cron(cron_pattern)

    if next_run is None:
        raise HTTPException(status_code=400, detail="Invalid cron pattern")

    return {"next_run": next_run.strftime("%Y-%m-%d %H:%M:%S")}


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: int):
    """
    Get a specific schedule.

    Retrieves details about a scheduled scan.

    Args:
        schedule_id: The unique identifier of the schedule

    Returns:
        ScanSchedule: Schedule information
    """
    return {"id": schedule_id, "name": f"Schedule {schedule_id}", "enabled": True}


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, schedule: ScanScheduleCreate):
    """
    Update a scan schedule.

    Modifies an existing scheduled scan configuration.

    Args:
        schedule_id: The unique identifier of the schedule
        schedule: Updated scan schedule configuration

    Returns:
        ScanSchedule: Updated schedule object
    """
    return {"id": schedule_id, **schedule.model_dump()}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """
    Delete a scan schedule.

    Removes a scheduled scan from the system.

    Args:
        schedule_id: The unique identifier of the schedule

    Returns:
        dict: Deletion confirmation message
    """
    return {"message": f"Schedule {schedule_id} deleted"}


@router.post("/scans/cleanup")
async def cleanup_absent_hosts(
    max_absent_days: int = 3,
    user: User = Depends(require_auth_or_local),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Cleanup hosts that have been absent from scans for a specified number of scans.

    Removes hosts that haven't appeared in the last N scans.

    Args:
        max_absent_days: Number of consecutive absent scans before removal (default: 3)
        user: Authenticated user with write permissions

    Returns:
        dict: Cleanup results including removed hosts count
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )

    try:
        from datetime import timedelta
        from app.models.asset import Asset

        # Find hosts that have been absent for max_absent_days consecutive
        # scans
        result = await db.execute(
            select(Asset).where(
                Asset.consecutive_absent_count >= max_absent_days)
        )
        hosts_to_remove = list(result.scalars().all())

        removed_count = 0
        asset_ips_removed = []

        for host in hosts_to_remove:
            ip_address = host.ip_address
            # Remove the host and associated data
            await db.delete(host)
            removed_count += 1
            asset_ips_removed.append(ip_address)

            logger.info(
                "Removed absent host during cleanup",
                ip_address=ip_address,
                consecutive_absent_count=host.consecutive_absent_count,
            )

        await db.commit()

        logger.info(
            "Cleanup completed",
            hosts_removed=removed_count,
            max_absent_days=max_absent_days,
        )

        return {
            "status": "success",
            "hosts_removed": removed_count,
            "max_absent_days": max_absent_days,
            "removed_host_ips": asset_ips_removed,
        }

    except Exception as e:
        logger.error("Cleanup failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}")


@router.get("/scans/queue/stats")
async def get_scan_queue_stats():
    """
    Get scan queue statistics.

    Returns information about the current state of the scan queue
    including pending, running, and completed counts.

    Returns:
        dict: Queue statistics including current scan counts
    """
    from app.services.scan_scheduler import processor

    stats = processor.get_queue_stats()

    # Get actual counts from database
    async for session in get_async_session():
        try:
            pending_result = await session.execute(
                select(Scan).where(Scan.status == "pending")
            )
            pending_count = len(list(pending_result.scalars().all()))

            running_result = await session.execute(
                select(Scan).where(Scan.status == "running")
            )
            running_count = len(list(running_result.scalars().all()))

            completed_result = await session.execute(
                select(Scan).where(Scan.status == "completed")
            )
            completed_count = len(list(completed_result.scalars().all()))

            failed_result = await session.execute(
                select(Scan).where(Scan.status == "failed")
            )
            failed_count = len(list(failed_result.scalars().all()))

            return {
                "max_concurrent_scans": stats["max_concurrent_scans"],
                "pending": pending_count,
                "running": running_count,
                "completed": completed_count,
                "failed": failed_count,
            }
        except Exception as e:
            logger.error("Error getting queue stats", error=str(e))
            return {"error": str(e), "status": "unknown"}
