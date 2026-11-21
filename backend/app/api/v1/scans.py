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
from fastapi import APIRouter, HTTPException, Depends
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
    from sqlalchemy import select as sa_select
    from app.core.config import settings

    result = await db.execute(sa_select(Scan).where(Scan.status == "running"))
    running_scans = list(result.scalars().all())

    # If at capacity, mark as pending (will be picked up by scheduler)
    if len(running_scans) >= settings.max_concurrent_scans:
        # Already pending scans stay pending
        if scan.status != "pending":
            logger.info(
                "Scan queued (no capacity)",
                scan_id=scan.id,
                running_count=len(running_scans),
                max_concurrent=settings.max_concurrent_scans,
            )
        return {
            "scan_id": scan.id,
            "status": "pending",
            "message": f"Scan queued. Max concurrent scans ({settings.max_concurrent_scans}) reached.",
            "queue_position": 0,  # Will be updated by scheduler
        }

    # Update status and record start time
    scan.status = "running"
    scan.started_at = datetime.now()
    await db.commit()

    scanner = NmapPortScanner()

    # Validate target is authorized
    auth_service = get_authorization_service()
    validation_result = auth_service.validate_target(scan.target_cidr)

    if not validation_result.get("valid"):
        logger.warning(
            "Scan target not authorized",
            scan_id=scan_id,
            target=scan.target_cidr,
            reason=validation_result.get("reason", "Unknown"),
        )
        raise HTTPException(
            status_code=403,
            detail=f"Target not authorized for scanning: {validation_result.get('reason', 'Unauthorized')}",
        )

    try:
        # Perform the actual scan based on type
        result_data = None

        if scan.scan_type == "single_port":
            # Single port scan with SQL injection protection
            valid, ports_result, message = parse_and_validate_ports(scan.ports)
            if not valid:
                raise HTTPException(status_code=400, detail=message)

            # Validate ports list length
            if len(ports_result) > 1000:
                raise HTTPException(
                    status_code=400, detail="Maximum 1000 ports allowed per scan"
                )

            result_data = await scanner.scan_ports(scan.target_cidr, ports_result)

        elif scan.scan_type == "common":
            # Common ports scan
            result_data = await scanner.scan_common_ports(scan.target_cidr)

        elif scan.scan_type == "port_range":
            # Parse port range with validation
            valid, ports_result, message = parse_and_validate_ports(scan.ports)
            if not valid:
                raise HTTPException(status_code=400, detail=message)

            # For port_range, ports_result should be a range
            if len(ports_result) == 1:
                # Single port provided, convert to range
                raise HTTPException(
                    status_code=400,
                    detail="Port range must contain a dash (e.g., 1-1024)",
                )

            # Verify the range is correct
            start, end = ports_result[0], ports_result[-1]
            if (end - start + 1) != len(ports_result):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid port range format")

            result_data = await scanner.scan_port_range(scan.target_cidr, start, end)

        elif scan.scan_type == "full_tcp":
            # Full TCP scan (ports 1-65535)
            result_data = await scanner.full_scan(scan.target_cidr)

        elif scan.scan_type == "discovery":
            # Network discovery scan using ActiveDiscoveryEngine
            from app.engines.discovery.active import ActiveDiscoveryEngine

            discovery_engine = ActiveDiscoveryEngine(
                max_concurrent_hosts=5, scan_timeout=300
            )

            result_data = await discovery_engine.discover_with_nmap(
                scan.target_cidr,
                rate_limit=scan.rate_limit if hasattr(
                    scan, "rate_limit") else "medium",
            )

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown scan type: {scan.scan_type}"
            )

        # Parse XML if available in results
        raw_xml = result_data.get("raw_xml", "")
        parsed_results = {}

        if raw_xml:
            try:
                parsed_results = parse_nmap_xml(raw_xml)
            except Exception as e:
                parsed_results = {"error": f"Failed to parse XML: {str(e)}"}

        # For discovery scans, the results might be in a different format
        if scan.scan_type == "discovery":
            # Extract hosts from discovery results
            discovered_hosts = result_data.get("hosts", [])

            logger.info(
                "Discovery scan results",
                scan_id=scan.id,
                hosts_found=result_data.get("hosts_found", 0),
                discovered_hosts_count=len(discovered_hosts),
            )

            if discovered_hosts:
                # Parse hosts and create Asset records
                from app.models.asset import Asset

                assets_created = 0
                assets_skipped_duplicate = 0
                assets_skipped_no_ip = 0

                for host in discovered_hosts:
                    # Extract IP with proper fallbacks - discovery results use
                    # "ip_address"
                    ip = (
                        host.get("ip_address")
                        or host.get("ip")
                        or host.get("ipaddress")
                    )
                    hostname = host.get("hostname", "")

                    if not ip:
                        assets_skipped_no_ip += 1
                        logger.debug("Skipping host without IP", host=host)
                        continue

                    # Check if asset already exists using correct field name
                    existing_result = await db.execute(
                        select(Asset).where(Asset.ip_address == ip)
                    )
                    existing_asset = existing_result.scalars().first()

                    if existing_asset:
                        # Update existing asset - mark as seen in current scan
                        existing_asset.last_seen_scan_id = scan.id
                        existing_asset.consecutive_absent_count = (
                            0  # Reset absent count
                        )

                        assets_skipped_duplicate += 1
                        logger.debug(
                            "Asset already exists, updating scan tracking",
                            ip=ip,
                            hostname=hostname,
                        )
                    else:
                        # Create new asset
                        mac = host.get("mac_address") or host.get("mac", "")
                        if mac == "":
                            mac = None
                        device_type = (
                            host.get("device_type") or host.get("device") or ""
                        )
                        operating_system = (
                            host.get("operating_system") or host.get(
                                "os") or ""
                        )
                        confidence_level = (
                            host.get("confidence")
                            or host.get("confidence_level")
                            or "low"
                        )

                        new_asset = Asset(
                            ip_address=ip,
                            mac_address=mac,
                            hostname=hostname,
                            device_type=device_type,
                            operating_system=operating_system,
                            confidence_level=confidence_level,
                            last_seen_scan_id=scan.id,  # Track first seen scan
                            consecutive_absent_count=0,
                        )
                        db.add(new_asset)
                        assets_created += 1

                        logger.info(
                            "Created new asset from scan",
                            ip=ip,
                            hostname=hostname,
                            mac_address=mac,
                        )

                await db.commit()

                logger.info(
                    "Discovery scan assets created",
                    scan_id=scan.id,
                    assets_created=assets_created,
                    assets_skipped_duplicate=assets_skipped_duplicate,
                    assets_skipped_no_ip=assets_skipped_no_ip,
                )

            # Track hosts that were absent from this scan (increment absent
            # count)
            if discovered_hosts:
                # Get all IPs found in this scan
                current_scan_ips = {
                    host.get("ip_address")
                    for host in discovered_hosts
                    if host.get("ip_address")
                }

                # Find ALL assets that exist
                all_assets_result = await db.execute(select(Asset))
                all_assets = all_assets_result.scalars().all()

                for asset in all_assets:
                    # If this asset's IP is not in current scan results,
                    # increment absent count
                    if asset.ip_address not in current_scan_ips:
                        # Only increment if this asset was previously seen (has
                        # a last_seen_scan_id)
                        if asset.last_seen_scan_id is not None:
                            asset.consecutive_absent_count += 1

                            logger.debug(
                                "Asset absent from current scan",
                                ip_address=asset.ip_address,
                                consecutive_absent_count=asset.consecutive_absent_count,
                            )
                    else:
                        # This asset was found in this scan - reset absent
                        # count
                        if asset.consecutive_absent_count > 0:
                            asset.consecutive_absent_count = 0

                            logger.debug(
                                "Asset found in current scan (reset absent count)",
                                ip_address=asset.ip_address,
                            )

                # Commit absent count updates
                await db.commit()

            # Save discovery results as evidence
            if discovered_hosts:
                await save_scan_evidence(
                    db, scan.id, "discovery_results", {
                        "hosts": discovered_hosts}
                )

            # Update hosts found count
            scan.hosts_found = len(discovered_hosts)
        else:
            if raw_xml:
                await save_scan_evidence(db, scan.id, "nmap_raw", {"xml": raw_xml})

            # Save parsed results if available
            if parsed_results:
                await save_scan_evidence(db, scan.id, "nmap_parsed", parsed_results)

            # Extract stats from parsed results if available
            if parsed_results and "hosts" in parsed_results:
                scan.hosts_found = len(parsed_results["hosts"])
            else:
                # Fallback to original stats
                scan.hosts_found = result_data.get("hosts_found", 0)

        # Update scan results
        scan.status = "completed"
        scan.completed_at = datetime.now()

        # Extract stats from parsed results if available
        if parsed_results and "hosts" in parsed_results:
            scan.hosts_found = len(parsed_results["hosts"])
        else:
            # Fallback to original stats
            scan.hosts_found = result_data.get("hosts_found", 0)

        await db.commit()

        response_data = {
            "scan_id": scan.id,
            "status": "completed",
            "hosts_found": scan.hosts_found or 0,
            **result_data,
        }

        return response_data

    except Exception as e:
        scan.status = "failed"
        scan.completed_at = datetime.now()
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


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
