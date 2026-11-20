# NetScope Discovery API

"""
API endpoints for network discovery operations.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_async_session
from app.models.asset import Asset
from app.schemas.asset import Asset as AssetSchema
import structlog
from app.engines.discovery.active import ActiveDiscoveryEngine
from app.engines.discovery.passive import PassiveDiscoveryEngine
from app.core.authorization_service import get_authorization_service

logger = structlog.get_logger(__name__)

router = APIRouter()


async def save_asset_to_db(db: AsyncSession, host_data: dict) -> Optional[Asset]:
    """
    Save a discovered asset to the database with deduplication.
    
    Checks for existing assets by IP address and MAC address before creating
    new records to prevent duplication.
    
    Args:
        db: Database session
        host_data: Dictionary containing host information
        
    Returns:
        Saved or updated Asset object
    """
    ip_address = host_data.get("ip_address")
    mac_address = host_data.get("mac_address")
    
    if not ip_address:
        return None
    
    # First check by IP address
    result = await db.execute(
        select(Asset).where(Asset.ip_address == ip_address)
    )
    existing = result.scalars().first()
    
    # If not found by IP, check by MAC address for deduplication
    if not existing and mac_address:
        result = await db.execute(
            select(Asset).where(Asset.mac_address == mac_address)
        )
        existing = result.scalars().first()
    
    if existing:
        # Update existing asset with new information
        for key, value in host_data.items():
            if value is not None:
                setattr(existing, key, value)
        return existing
    else:
        # Create new asset
        asset = Asset(**host_data)
        db.add(asset)
        return asset


@router.get("/discovery/passive")
async def passive_discovery(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Perform passive network discovery.
    
    Uses available network traffic and local information
    to identify hosts without active scanning. This method is
    non-intrusive and does not send packets to targets.
    
    Returns:
        dict: Discovery results with hosts found
    """
    engine = PassiveDiscoveryEngine()
    
    try:
        result = await engine.run_passive_scan()
        
        # Store discovered assets with deduplication
        saved_count = 0
        
        for host in result.get("hosts", []):
            asset = await save_asset_to_db(db, host)
            if asset:
                saved_count += 1
        
        await db.commit()
        
        return {
            "discovery_method": "passive",
            "hosts_found": result.get("hosts_found", 0),
            "assets_saved": saved_count,
            "status": "completed"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery/active")
async def active_discovery(
    target: str,
    rate_limit: str = "medium",
    db: AsyncSession = Depends(get_async_session)
):
    """
    Perform active network discovery.
    
    Probes the network using Nmap to identify hosts. This method
    sends packets to targets and may be detected by security systems.
    
    Args:
        target: Target IP address or CIDR range
        rate_limit: Scan speed preset (slow, medium, fast, aggressive)
        
    Returns:
        dict: Discovery results with hosts found and assets saved
        
    Raises:
        HTTPException(403): If target not authorized for scanning
        HTTPException(500): If discovery fails
    """
    
    # Validate target is authorized
    auth_service = get_authorization_service()
    validation_result = auth_service.validate_target(target)
    
    if not validation_result.get("valid"):
        logger.warning(
            "Discovery target not authorized",
            target=target,
            reason=validation_result.get("reason", "Unknown")
        )
        raise HTTPException(
            status_code=403,
            detail=f"Target not authorized for discovery: {validation_result.get('reason', 'Unauthorized')}"
        )
    
    engine = ActiveDiscoveryEngine()
    
    try:
        result = await engine.run_active_scan([target])
        
        # Store discovered assets with deduplication
        hosts_found = 0
        
        for res in result.get("results", []):
            if res["type"] == "hosts":
                hosts_data = res.get("data", {})
                discovered_hosts = hosts_data.get("hosts", [])
                hosts_found += len(discovered_hosts)
                
                for host in discovered_hosts:
                    # Only save fields that exist in Asset model
                    asset_data = {
                        "ip_address": host.get("ip_address"),
                        "mac_address": host.get("mac_address"),
                        "hostname": host.get("hostname"),
                        "vendor": host.get("vendor"),
                    }
                    asset = await save_asset_to_db(db, asset_data)
        
        await db.commit()
        
        # Count unique hosts found
        unique_hosts = len([
            res for res in result.get("results", [])
            if res["type"] == "hosts"
        ])
        
        return {
            "discovery_method": "active",
            "targets_scanned": 1,
            "hosts_found": hosts_found,
            "assets_saved": unique_hosts,
            "status": "completed"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/interfaces")
async def discover_interfaces():
    """
    Discover local network interfaces.
    
    Returns information about the system's network interfaces
    including IP addresses, MAC addresses, and interface status.
    
    Returns:
        dict: Network interfaces with details
    """
    engine = ActiveDiscoveryEngine()
    
    try:
        interfaces = await engine.discover_interfaces()
        
        return {
            "interfaces": interfaces,
            "count": len(interfaces),
            "status": "completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/gateways")
async def discover_gateways():
    """
    Discover network gateways.
    
    Returns information about configured gateways
    and default routes from the routing table.
    
    Returns:
        dict: Network gateways with details
    """
    engine = ActiveDiscoveryEngine()
    
    try:
        gateways = await engine.discover_gateways()
        
        return {
            "gateways": gateways,
            "count": len(gateways),
            "status": "completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets", response_model=list[AssetSchema])
async def list_assets(
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all discovered assets.
    
    Returns a list of all assets in the system with basic information.
    
    Returns:
        List[AssetSchema]: Array of asset objects
    """
    result = await db.execute(select(Asset))
    return list(result.scalars().all())


@router.get("/assets/{ip_address}", response_model=AssetSchema)
async def get_asset(
    ip_address: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific asset by IP address.
    
    Retrieves detailed information about an asset using its IP address.
    
    Args:
        ip_address: The IP address of the asset
        
    Returns:
        AssetSchema: Asset information
        
    Raises:
        HTTPException(404): If asset not found
    """
    result = await db.execute(
        select(Asset).where(Asset.ip_address == ip_address)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return asset
