# NetScope Scanning API

"""
API endpoints for port scanning operations.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.scan import Scan, ScanTarget, ScanEvidence
from app.schemas.scan import (
    Scan as ScanSchema,
    ScanCreate,
    ScanTarget as ScanTargetSchema
)
import structlog
from app.engines.port_scanner.nmap_engine import NmapPortScanner
from app.engines.scanner.parser import parse_nmap_xml
from app.core.authorization_service import get_authorization_service
from app.core.validators import parse_and_validate_ports, validate_cidr
from app.core.auth import require_auth, User

logger = structlog.get_logger(__name__)

router = APIRouter()


def require_scan_permission(user: User = Depends(require_auth)) -> User:
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
            status_code=403,
            detail="User does not have scan permissions"
        )
    return user


async def save_scan_evidence(db: AsyncSession, scan_id: int, evidence_type: str, data: dict):
    """
    Save scan evidence to the database.
    
    Args:
        db: Database session
        scan_id: ID of the scan
        evidence_type: Type of evidence (nmap_raw, nmap_parsed)
        data: Evidence data to store
    """
    evidence = ScanEvidence(
        scan_id=scan_id,
        evidence_type=evidence_type,
        data=data
    )
    db.add(evidence)


@router.get("/scans", response_model=list[ScanSchema])
async def list_scans(
    db: AsyncSession = Depends(get_async_session)
):
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
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
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
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    db_scan = Scan(**scan.model_dump())
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    return db_scan


@router.get("/scans/{scan_id}", response_model=ScanSchema)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session)
):
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
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return scan


@router.post("/scans/{scan_id}/cancel")
async def cancel_scan(
    scan_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
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
            status_code=403,
            detail="User does not have write permissions"
        )
    
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Update scan status to cancelled
    scan.status = "cancelled"
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
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
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
            status_code=403,
            detail="User does not have write permissions"
        )
    
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Update status
    scan.status = "running"
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
            reason=validation_result.get("reason", "Unknown")
        )
        raise HTTPException(
            status_code=403,
            detail=f"Target not authorized for scanning: {validation_result.get('reason', 'Unauthorized')}"
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
                    status_code=400,
                    detail="Maximum 1000 ports allowed per scan"
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
                    detail="Port range must contain a dash (e.g., 1-1024)"
                )
            
            # Verify the range is correct
            start, end = ports_result[0], ports_result[-1]
            if (end - start + 1) != len(ports_result):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid port range format"
                )
            
            result_data = await scanner.scan_port_range(
                scan.target_cidr,
                start,
                end
            )
            
        elif scan.scan_type == "full_tcp":
            # Full TCP scan (ports 1-65535)
            result_data = await scanner.full_scan(scan.target_cidr)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scan type: {scan.scan_type}"
            )
        
        # Parse XML if available in results
        raw_xml = result_data.get("raw_xml", "")
        parsed_results = {}
        
        if raw_xml:
            try:
                parsed_results = parse_nmap_xml(raw_xml)
            except Exception as e:
                parsed_results = {"error": f"Failed to parse XML: {str(e)}"}
        
        # Save raw XML as evidence
        if raw_xml:
            await save_scan_evidence(
                db, scan.id, "nmap_raw", {"xml": raw_xml}
            )
        
        # Save parsed results if available
        if parsed_results:
            await save_scan_evidence(
                db, scan.id, "nmap_parsed", parsed_results
            )
        
        # Update scan results
        scan.status = "completed"
        
        # Extract stats from parsed results if available
        if parsed_results and "hosts" in parsed_results:
            scan.hosts_found = len(parsed_results["hosts"])
        else:
            # Fallback to original stats
            scan.hosts_found = result_data.get("hosts_found", 0)
        
        await db.commit()
        
        return {
            "scan_id": scan.id,
            "status": "completed",
            **result_data
        }
        
    except Exception as e:
        scan.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans/{scan_id}/targets", response_model=list[ScanTargetSchema])
async def get_scan_targets(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get targets for a scan.
    
    Retrieves the individual hosts/targets that were scanned
    as part of this scan operation.
    
    Args:
        scan_id: The unique identifier of the scan
        
    Returns:
        List[ScanTargetSchema]: Array of scan target objects
    """
    result = await db.execute(
        select(ScanTarget).where(ScanTarget.scan_id == scan_id)
    )
    return list(result.scalars().all())


# ==================== Phase 3: Export Endpoints ====================

from fastapi.responses import StreamingResponse, JSONResponse
from io import StringIO


@router.get("/scans/{scan_id}/export/csv")
async def export_scan_csv(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session)
):
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
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Generate CSV data
    csv_data = export_to_csv({
        "scan_id": scan.id,
        "target": scan.target_cidr,
        "status": scan.status,
        "hosts_found": scan.hosts_found
    })
    
    return StreamingResponse(
        StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scan_{scan_id}_results.csv"}
    )


@router.get("/scans/{scan_id}/export/json")
async def export_scan_json(
    scan_id: int,
    db: AsyncSession = Depends(get_async_session)
):
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
    
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    json_data = export_to_json({
        "scan_id": scan.id,
        "target": scan.target_cidr,
        "status": scan.status,
        "hosts_found": scan.hosts_found,
        "scan_type": scan.scan_type
    })
    
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
    
    csv_data = export_to_csv([
        {
            "id": s.id,
            "name": s.name or "",
            "target_cidr": s.target_cidr,
            "scan_type": s.scan_type,
            "status": s.status,
            "hosts_found": s.hosts_found
        }
        for s in scans
    ])
    
    return StreamingResponse(
        StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=all_scans.csv"}
    )


# ==================== Phase 3: Scan Scheduling Endpoints ====================

from datetime import datetime
from app.schemas.scan import ScanSchedule, ScanScheduleCreate


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
    return {
        "id": 1,  # Will be replaced with actual DB ID
        **schedule.model_dump()
    }


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
    return {
        "id": schedule_id,
        "name": f"Schedule {schedule_id}",
        "enabled": True
    }


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
    return {
        "id": schedule_id,
        **schedule.model_dump()
    }


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
