# NetScope Vulnerabilities API

"""
API endpoints for vulnerability management.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_async_session
from app.models.vulnerability import (
    Vulnerability,
    IntelligenceSync,
    RiskFinding,
    VulnerabilityKEV,
    VulnerabilityEPSS_History,
)
from app.engines.vulnerability.intelligence import IntelligenceSync as IntelSyncEngine
from app.core.auth import require_auth, User
from app.schemas.vulnerability import (
    VulnerabilityResponse,
    VulnerabilityListResponse,
    CVSSData,
    EPSSData,
    KEVData,
)

router = APIRouter()


def require_write_permission(user: User = Depends(require_auth)) -> User:
    """Require user with write permissions."""
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )
    return user


@router.get("/vulnerabilities", response_model=list[VulnerabilityListResponse])
async def list_vulnerabilities(
    db: AsyncSession = Depends(get_async_session),
    limit: int = 100,
    offset: int = 0,
    is_kev: bool = Query(default=None, description="Filter by KEV status"),
    epss_min: float = Query(
        default=None,
        description="Minimum EPSS score filter"),
    epss_max: float = Query(
        default=None,
        description="Maximum EPSS score filter"),
):
    """List vulnerabilities with optional filtering.

    Supports filtering by:
    - is_kev: Filter for KEV entries (true) or non-KEV entries (false)
    - epss_min: Minimum EPSS score
    - epss_max: Maximum EPSS score

    Returns a list of vulnerability summaries with CVSS, KEV status, and EPSS data.
    """
    # Build the main query with joins
    # We need to join Vulnerability with:
    # 1. Latest EPSS history record (subquery)
    # 2. KEV info (one-to-one)

    # Subquery to get the most recent EPSS observation for each vulnerability
    epss_subquery = (
        select(
            VulnerabilityEPSS_History.vulnerability_id,
            func.max(VulnerabilityEPSS_History.observed_at).label(
                "max_observed"),
        )
        .group_by(VulnerabilityEPSS_History.vulnerability_id)
        .subquery()
    )

    epss_latest = (
        select(VulnerabilityEPSS_History).join(
            epss_subquery,
            (
                VulnerabilityEPSS_History.vulnerability_id
                == epss_subquery.c.vulnerability_id
            )
            & (VulnerabilityEPSS_History.observed_at == epss_subquery.c.max_observed),
        )
    ).subquery()

    # Build the main query
    query = (
        select(Vulnerability)
        .join(
            VulnerabilityKEV,
            Vulnerability.id == VulnerabilityKEV.vulnerability_id,
            isouter=True,
        )
        .join(
            epss_latest,
            Vulnerability.id == epss_latest.c.vulnerability_id,
            isouter=True,
        )
    )

    # Apply filters
    if is_kev is not None:
        if is_kev:
            query = query.where(VulnerabilityKEV.id.isnot(None))
        else:
            query = query.where(VulnerabilityKEV.id.is_(None))

    if epss_min is not None:
        query = query.where(epss_latest.c.epss_score >= epss_min)

    if epss_max is not None:
        query = query.where(epss_latest.c.epss_score <= epss_max)

    # Add limit and offset
    query = query.limit(limit).offset(offset)

    # Execute the query
    result = await db.execute(query)
    vulnerabilities = result.scalars().unique().all()

    # Transform to response models
    responses = []
    for vuln in vulnerabilities:
        # Get KEV data if exists
        kev_data = None
        if vuln.kev_info:
            kev_data = KEVData(
                is_kev=True,
                date_added=(
                    vuln.kev_info.date_added.date()
                    if vuln.kev_info.date_added
                    else None
                ),
                due_date=(
                    vuln.kev_info.due_date.date() if vuln.kev_info.due_date else None
                ),
            )

        # Get latest EPSS data if exists
        epss_data = None
        for history in vuln.epss_history:
            if epss_data is None or (
                history.observed_at and history.observed_at > epss_data.observed_at
            ):
                if history.epss_score is not None:
                    epss_data = EPSSData(
                        score=history.epss_score, percentile=history.epss_percentile
                    )

        response = VulnerabilityListResponse(
            cve_id=vuln.cve_id,
            description=vuln.description,
            cvss_score=vuln.cvss_score,
            severity=vuln.severity,
            epss_score=epss_data.score if epss_data else None,
            is_kev=bool(kev_data),
            published_date=vuln.published_date,
        )
        responses.append(response)

    return responses


@router.get("/vulnerabilities/{cve_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
        cve_id: str, db: AsyncSession = Depends(get_async_session)):
    """Get a vulnerability by CVE ID.

    Returns a unified view of the vulnerability including:
    - Basic vulnerability data
    - CVSS scores
    - EPSS score (most recent observation)
    - KEV status and details
    """
    # Query Vulnerability with left joins for related data
    result = await db.execute(
        select(Vulnerability)
        .join(
            VulnerabilityKEV,
            Vulnerability.id == VulnerabilityKEV.vulnerability_id,
            isouter=True,
        )
        .join(
            VulnerabilityEPSS_History,
            Vulnerability.id == VulnerabilityEPSS_History.vulnerability_id,
            isouter=True,
        )
        .where(Vulnerability.cve_id == cve_id)
    )

    vuln = result.scalar_one_or_none()

    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    # Build KEV data if exists
    kev_data = None
    if vuln.kev_info:
        kev_data = KEVData(
            is_kev=True,
            date_added=(
                vuln.kev_info.date_added.date() if vuln.kev_info.date_added else None
            ),
            due_date=vuln.kev_info.due_date.date() if vuln.kev_info.due_date else None,
        )

    # Get latest EPSS score from history
    epss_data = None
    if vuln.epss_history:
        # Sort by observed_at and get the most recent
        sorted_history = sorted(
            vuln.epss_history, key=lambda x: x.observed_at or datetime.min, reverse=True
        )
        for history in sorted_history:
            if history.epss_score is not None:
                epss_data = EPSSData(
                    score=history.epss_score, percentile=history.epss_percentile
                )
                break

    # Build CVSS data
    cvss_data = None
    if vuln.cvss_score is not None:
        cvss_data = CVSSData(
            version=vuln.cvss_version or "3.1",
            score=vuln.cvss_score,
            severity=vuln.severity,
        )

    response = VulnerabilityResponse(
        cve_id=vuln.cve_id,
        description=vuln.description,
        cvss=cvss_data,
        epss=epss_data,
        kev=kev_data,
        published_date=vuln.published_date,
        last_modified_date=vuln.last_modified_date,
    )

    return response


@router.get("/vulnerabilities/{cve_id}/intelligence")
async def get_vulnerability_intelligence(
    cve_id: str, db: AsyncSession = Depends(get_async_session)
):
    """Get intelligence data for a vulnerability."""
    engine = IntelSyncEngine()

    try:
        result = await engine.get_intelligence_for_cve(cve_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"No intelligence data found for {cve_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vulnerabilities/kev")
async def list_kev(db: AsyncSession = Depends(
        get_async_session), limit: int = 100):
    """List CISA KEV entries."""
    engine = IntelSyncEngine()

    try:
        result = await engine.cisa_client.get_kev_entries(limit=limit)

        return {"entries": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vulnerabilities/stats")
async def get_vuln_stats(db: AsyncSession = Depends(get_async_session)):
    """Get vulnerability statistics."""
    # Get total vulnerabilities count
    vuln_result = await db.execute(select(func.count(Vulnerability.id)))
    total_vulns = vuln_result.scalar_one()

    # Get KEV count
    kev_result = await db.execute(select(func.count(VulnerabilityKEV.id)))
    kev_count = kev_result.scalar_one()

    # Get critical count (CVSS >= 9.0)
    critical_result = await db.execute(
        select(
            func.count(
                Vulnerability.id)).where(
            Vulnerability.cvss_score >= 9.0)
    )
    critical_count = critical_result.scalar_one()

    return {
        "total_vulnerabilities": total_vulns,
        "kev_count": kev_count,
        "critical_count": critical_count,
    }


@router.post("/intelligence/sync")
async def sync_intelligence(
    db: AsyncSession = Depends(get_async_session), user: User = Depends(require_auth)
):
    """Sync vulnerability intelligence from all sources and persist to database.

    Triggers sync for:
    - CISA KEV catalog
    - NVD CVE database
    - EPSS scores

    Persists all data to the local database with proper deduplication.

    Returns combined results from all three sources.
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )

    engine = IntelSyncEngine()

    try:
        # This calls sync_to_database which persists all data to the database
        result = await engine.sync_to_database(db)

        return {"status": "completed", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/status")
async def get_intelligence_status(
        db: AsyncSession = Depends(get_async_session)):
    """Get intelligence synchronization status."""
    result = await db.execute(select(IntelligenceSync))
    syncs = list(result.scalars().all())

    return {
        "syncs": [
            {
                "source": s.source_name,
                "last_sync": s.last_sync.isoformat() if s.last_sync else None,
                "status": s.sync_status,
            }
            for s in syncs
        ]
    }


@router.post("/vulnerabilities/correlate")
async def correlate_vulnerabilities(user: User = Depends(require_auth)):
    """
    Correlate discovered services with vulnerabilities.

    This endpoint would correlate assets with the vulnerability database
    and create vulnerability findings.
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403, detail="User does not have write permissions"
        )

    return {"message": "Correlation started", "status": "pending"}


@router.get("/risk/findings", response_model=list)
async def get_risk_findings():
    """Get risk findings."""
    return []


@router.get("/risk/findings/{finding_id}")
async def get_risk_finding(
    finding_id: int, db: AsyncSession = Depends(get_async_session)
):
    """Get a specific risk finding."""
    result = await db.execute(select(RiskFinding).where(RiskFinding.id == finding_id))
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(status_code=404, detail="Risk finding not found")

    return finding
