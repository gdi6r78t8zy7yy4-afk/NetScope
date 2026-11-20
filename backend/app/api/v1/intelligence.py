# NetScope Intelligence API

"""
API endpoints for vulnerability intelligence data.
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
from app.core.auth import require_auth

router = APIRouter(prefix="/api/v1/intelligence", tags=["Intelligence"])


@router.get("/cve/{cve_id}", dependencies=[Depends(require_auth)])
async def get_cve_intelligence(
    cve_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get complete intelligence information for a CVE.
    
    Returns combined data from multiple sources:
    - CISA KEV catalog (known exploited vulnerabilities)
    - NVD CVE database (National Vulnerability Database)
    - EPSS scores (Exploit Prediction Scoring System)
    
    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")
        
    Returns:
        Complete CVE intelligence report with scores, KEV status, and exploit data
        
    Raises:
        HTTPException(404): If CVE not found in any intelligence source
        HTTPException(500): If data retrieval fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.get_intelligence_for_cve(cve_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"CVE {cve_id} not found in any intelligence source"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/cves", dependencies=[Depends(require_auth)])
async def sync_cves(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Sync CVE data from NVD.
    
    Fetches recent CVEs from the National Vulnerability Database
    and updates the local database with latest vulnerability information.
    
    Returns:
        dict: Sync results including count and status
        
    Raises:
        HTTPException(500): If sync operation fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.sync_nvd()
        
        return {
            "status": "completed",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/kev", dependencies=[Depends(require_auth)])
async def sync_kev(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Sync CISA KEV catalog.
    
    Fetches the complete CISA Known Exploited Vulnerabilities (KEV) catalog
    and updates local data with known exploited vulnerabilities.
    
    Returns:
        dict: Sync results including catalog count and status
        
    Raises:
        HTTPException(500): If sync operation fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.sync_cisa_kev()
        
        return {
            "status": "completed",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/epss", dependencies=[Depends(require_auth)])
async def sync_epss(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Sync EPSS scores.
    
    Fetches top CVEs by EPSS percentile from FIRST.org and updates
    local data with exploit probability scores.
    
    Returns:
        dict: Sync results including EPSS count and status
        
    Raises:
        HTTPException(500): If sync operation fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.sync_epss()
        
        return {
            "status": "completed",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/epss/{cve_id}", dependencies=[Depends(require_auth)])
async def get_epss_score(
    cve_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get EPSS score for a specific CVE.
    
    Retrieves the Exploit Prediction Scoring System (EPSS) score
    for a CVE, which estimates the probability of exploitation in the wild.
    
    Args:
        cve_id: CVE identifier
        
    Returns:
        dict: EPSS score data including percentile and probability
        
    Raises:
        HTTPException(404): If EPSS score not found
        HTTPException(500): If retrieval fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.get_epss_score(cve_id)
        
        if not result or not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"EPSS score not found for {cve_id}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kev/catalog", dependencies=[Depends(require_auth)])
async def get_kev_catalog(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get the complete CISA KEV catalog.
    
    Returns a summary of all known exploited vulnerabilities
    maintained by CISA with information about exploitation status.
    
    Returns:
        dict: KEV catalog summary
        
    Raises:
        HTTPException(500): If catalog retrieval fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.get_kev_catalog_summary()
        
        return {
            "catalog": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kev/entries", dependencies=[Depends(require_auth)])
async def get_kev_entries(
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get KEV entries from the catalog.
    
    Retrieves a list of known exploited vulnerabilities with
    limited information for listing purposes.
    
    Args:
        limit: Maximum number of entries to return (default: 100)
        
    Returns:
        dict: List of KEV entries with counts
        
    Raises:
        HTTPException(500): If retrieval fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.cisa_client.get_kev_entries(limit=limit)
        
        return {
            "entries": result,
            "count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kev/{cve_id}", dependencies=[Depends(require_auth)])
async def get_kev_entry(
    cve_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get KEV entry for a specific CVE.
    
    Retrieves detailed information about whether a CVE is in
    CISA's Known Exploited Vulnerabilities catalog.
    
    Args:
        cve_id: CVE identifier
        
    Returns:
        dict: KEV entry with exploitation details
        
    Raises:
        HTTPException(404): If CVE not found in KEV catalog
        HTTPException(500): If retrieval fails
    """
    engine = IntelSyncEngine()
    
    try:
        result = await engine.get_kev_entry(cve_id)
        
        if not result or not result.get("in_kev", False):
            raise HTTPException(
                status_code=404,
                detail=f"{cve_id} not found in CISA KEV catalog"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", dependencies=[Depends(require_auth)])
async def get_intelligence_status(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get intelligence synchronization status.
    
    Returns the current sync status of all intelligence sources
    including last successful sync time and record counts.
    
    Returns:
        dict: Status of all intelligence sources
        
    Raises:
        HTTPException(500): If status retrieval fails
    """
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


@router.get("/correlate/{asset_id}", dependencies=[Depends(require_auth)])
async def correlate_asset_vulnerabilities(
    asset_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Correlate vulnerabilities for a specific asset.
    
    Links discovered services on an asset with known vulnerabilities
    to create risk findings with priority scores.
    
    Args:
        asset_id: Asset ID to correlate vulnerabilities for
        
    Returns:
        dict: Correlated vulnerabilities with risk scores and findings
        
    Raises:
        HTTPException(404): If asset not found
        HTTPException(500): If correlation fails
    """
    from app.engines.vulnerability.correlation import VulnerabilityCorrelator
    
    engine = IntelSyncEngine()
    correlator = VulnerabilityCorrelator()
    
    try:
        # Get asset services
        from app.models.asset import Asset, HostProfile
        
        asset_result = await db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail=f"Asset {asset_id} not found"
            )
        
        # Get host profile for asset
        profile_result = await db.execute(
            select(HostProfile).where(HostProfile.asset_id == asset_id)
        )
        host_profile = profile_result.scalar_one_or_none()
        
        if not host_profile:
            raise HTTPException(
                status_code=404,
                detail=f"No host profile found for asset {asset_id}"
            )
        
        # Get all vulnerabilities with relationships loaded
        from app.models.vulnerability import VulnerabilityKEV, VulnerabilityEPSS_History
        
        vuln_result = await db.execute(
            select(Vulnerability)
            .options(
                selectinload(Vulnerability.kev_info),
                selectinload(Vulnerability.epss_history)
            )
        )
        vulnerabilities = list(vuln_result.scalars().all())
        
        # Convert to dict format with proper field handling
        vuln_list = []
        for v in vulnerabilities:
            # Get EPSS from latest history record
            epss_score = None
            if v.epss_history:
                sorted_history = sorted(
                    v.epss_history,
                    key=lambda x: x.observed_at or datetime.min,
                    reverse=True
                )
                if sorted_history[0].epss_score is not None:
                    epss_score = sorted_history[0].epss_score
            
            vuln_dict = {
                "cve_id": v.cve_id,
                "description": v.description,
                "cvss_score": v.cvss_score,
                "severity": v.severity,
            }
            
            # Add KEV info if available
            if v.kev_info:
                vuln_dict["is_kev"] = True
                vuln_dict["kev_date_added"] = v.kev_info.date_added
            else:
                vuln_dict["is_kev"] = False
            
            # Add EPSS score if available
            if epss_score is not None:
                vuln_dict["epss_score"] = epss_score
            
            vuln_list.append(vuln_dict)
        
        # Correlate
        findings = await correlator.correlate(host_profile.to_dict(), vuln_list)
        
        return {
            "asset_id": asset_id,
            "findings": findings,
            "total_findings": len(findings),
            "risk_score": sum(f.get("risk_score", 0) for f in findings)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
