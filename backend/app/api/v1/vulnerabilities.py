# NetScope Vulnerabilities API

"""
API endpoints for vulnerability management.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.vulnerability import (
    Vulnerability,
    IntelligenceSync,
    RiskFinding
)
from app.engines.vulnerability.intelligence import IntelligenceSync as IntelSyncEngine
from app.core.auth import require_auth, User

router = APIRouter()


def require_write_permission(user: User = Depends(require_auth)) -> User:
    """Require user with write permissions."""
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    return user


@router.get("/vulnerabilities", response_model=list)
async def list_vulnerabilities(
    db: AsyncSession = Depends(get_async_session),
    limit: int = 100
):
    """List vulnerabilities."""
    result = await db.execute(select(Vulnerability).limit(limit))
    return list(result.scalars().all())


@router.get("/vulnerabilities/{cve_id}")
async def get_vulnerability(
    cve_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a vulnerability by CVE ID."""
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.cve_id == cve_id)
    )
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    return vuln


@router.get("/vulnerabilities/{cve_id}/intelligence")
async def get_vulnerability_intelligence(
    cve_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get intelligence data for a vulnerability."""
    engine = IntelSyncEngine()
    
    try:
        result = await engine.get_intelligence_for_cve(cve_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No intelligence data found for {cve_id}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vulnerabilities/kev")
async def list_kev(
    db: AsyncSession = Depends(get_async_session),
    limit: int = 100
):
    """List CISA KEV entries."""
    engine = IntelSyncEngine()
    
    try:
        result = await engine.cisa_client.get_kev_entries(limit=limit)
        
        return {
            "entries": result,
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vulnerabilities/stats")
async def get_vuln_stats():
    """Get vulnerability statistics."""
    return {
        "total_vulnerabilities": 0,
        "kev_count": 0,
        "critical_count": 0
    }


@router.post("/intelligence/sync")
async def sync_intelligence(
    user: User = Depends(require_auth)
):
    """Sync vulnerability intelligence."""
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    engine = IntelSyncEngine()
    
    try:
        result = await engine.sync_all()
        
        return {
            "status": "completed",
            "results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/status")
async def get_intelligence_status(
    db: AsyncSession = Depends(get_async_session)
):
    """Get intelligence synchronization status."""
    result = await db.execute(select(IntelligenceSync))
    syncs = list(result.scalars().all())
    
    return {
        "syncs": [
            {
                "source": s.source_name,
                "last_sync": s.last_sync.isoformat() if s.last_sync else None,
                "status": s.sync_status
            }
            for s in syncs
        ]
    }


@router.post("/vulnerabilities/correlate")
async def correlate_vulnerabilities(
    user: User = Depends(require_auth)
):
    """
    Correlate discovered services with vulnerabilities.
    
    This endpoint would correlate assets with the vulnerability database
    and create vulnerability findings.
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    return {
        "message": "Correlation started",
        "status": "pending"
    }


@router.get("/risk/findings", response_model=list)
async def get_risk_findings():
    """Get risk findings."""
    return []


@router.get("/risk/findings/{finding_id}")
async def get_risk_finding(
    finding_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific risk finding."""
    result = await db.execute(
        select(RiskFinding).where(RiskFinding.id == finding_id)
    )
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Risk finding not found")
    
    return finding
