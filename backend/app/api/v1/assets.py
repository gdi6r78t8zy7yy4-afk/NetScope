# NetScope Assets API

"""
API endpoints for asset management.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.asset import Asset, Port, HostProfile
from app.models.asset_history import AssetHistory, ChangeType, get_asset_history
from app.schemas.asset import (
    Asset as AssetSchema,
    AssetCreate,
    Port as PortSchema,
    HostProfile as HostProfileSchema
)
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


@router.get("/assets", response_model=list[AssetSchema])
async def list_assets(
    db: AsyncSession = Depends(get_async_session)
):
    """
    List all discovered assets.
    
    Returns a list of all assets in the system with their basic information.
    
    Returns:
        List[AssetSchema]: Array of asset objects
    """
    result = await db.execute(select(Asset))
    return list(result.scalars().all())


@router.get("/assets/{asset_id}", response_model=AssetSchema)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get an asset by ID.
    
    Retrieves detailed information about a specific asset using its database ID.
    
    Args:
        asset_id: The unique identifier of the asset
        
    Returns:
        AssetSchema: Asset information including IP, hostname, device type
        
    Raises:
        HTTPException(404): If asset not found
    """
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return asset


@router.get("/assets/{ip_address}", response_model=AssetSchema)
async def get_asset_by_ip(
    ip_address: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get an asset by IP address.
    
    Retrieves asset information using its IP address.
    
    Args:
        ip_address: The IP address of the asset (e.g., "192.168.1.1")
        
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


@router.get("/assets/{asset_id}/ports", response_model=list[PortSchema])
async def get_asset_ports(
    asset_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get ports for an asset.
    
    Retrieves all scanned ports associated with a specific asset.
    
    Args:
        asset_id: The unique identifier of the asset
        
    Returns:
        List[PortSchema]: Array of port objects with state and service info
    """
    result = await db.execute(
        select(Port).where(Port.asset_id == asset_id)
    )
    return list(result.scalars().all())


@router.get("/assets/{asset_id}/vulnerabilities")
async def get_asset_vulnerabilities(
    asset_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get vulnerabilities for an asset.
    
    Retrieves vulnerability information and counts for a specific asset.
    
    Args:
        asset_id: The unique identifier of the asset
        
    Returns:
        dict: Vulnerability information including counts
        
    Raises:
        HTTPException(404): If asset not found
    """
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Return vulnerability count
    return {
        "ip_address": asset.ip_address,
        "vulnerability_count": asset.vulnerability_count,
        "kev_count": asset.kev_count
    }


@router.post("/assets", response_model=AssetSchema)
async def create_asset(
    asset: AssetCreate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new asset.
    
    Registers a new asset in the system with provided information.
    Requires write permissions.
    
    Args:
        asset: AssetCreate schema containing asset details
        user: Authenticated user with write permissions
        
    Returns:
        AssetSchema: Created asset object
        
    Raises:
        HTTPException(403): If user lacks write permissions
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    db_asset = Asset(**asset.model_dump())
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


@router.put("/assets/{asset_id}", response_model=AssetSchema)
async def update_asset(
    asset_id: int,
    asset: AssetCreate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update an asset.
    
    Updates existing asset information with provided fields.
    Requires write permissions.
    
    Args:
        asset_id: The unique identifier of the asset to update
        asset: AssetCreate schema with updated fields
        user: Authenticated user with write permissions
        
    Returns:
        AssetSchema: Updated asset object
        
    Raises:
        HTTPException(403): If user lacks write permissions
        HTTPException(404): If asset not found
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    db_asset = result.scalar_one_or_none()
    
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    for field, value in asset.model_dump(exclude_unset=True).items():
        setattr(db_asset, field, value)
    
    await db.commit()
    await db.refresh(db_asset)
    return db_asset


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete an asset.
    
    Removes an asset from the system. Requires write permissions.
    
    Args:
        asset_id: The unique identifier of the asset to delete
        user: Authenticated user with write permissions
        
    Returns:
        dict: Deletion confirmation message
        
    Raises:
        HTTPException(403): If user lacks write permissions
        HTTPException(404): If asset not found
    """
    # Check write permissions
    if "write" not in (user.scopes or []):
        raise HTTPException(
            status_code=403,
            detail="User does not have write permissions"
        )
    
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    await db.delete(asset)
    await db.commit()
    
    return {"message": "Asset deleted"}


@router.get("/assets/{asset_id}/profile", response_model=HostProfileSchema)
async def get_asset_profile(
    asset_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get host profile for an asset.
    
    Retrieves detailed host profiling information including OS fingerprinting,
    uptime, and service counts for a specific asset.
    
    Args:
        asset_id: The unique identifier of the asset
        
    Returns:
        HostProfileSchema: Detailed host profile information
        
    Raises:
        HTTPException(404): If host profile not found
    """
    result = await db.execute(
        select(HostProfile).where(HostProfile.asset_id == asset_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Host profile not found")
    
    return profile


@router.get("/assets/{asset_id}/history", response_model=list[dict])
async def get_asset_history_endpoint(
    asset_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get history entries for an asset.
    
    Retrieves all historical changes tracked for a specific asset,
    including OS updates, port changes, and vulnerability findings.
    
    Args:
        asset_id: The unique identifier of the asset
        limit: Maximum number of history entries to return
        
    Returns:
        List[dict]: Array of history entry objects
    """
    # Get asset to verify it exists
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get history entries
    from app.models.asset_history import AssetHistory, get_asset_history
    
    history = get_asset_history(asset_id, limit)
    
    # Convert to response format
    return [
        {
            "id": h.id,
            "asset_id": h.asset_id,
            "change_type": h.change_type,
            "changed_fields": h.changed_fields,
            "old_values": h.old_values,
            "new_values": h.new_values,
            "scan_id": h.scan_id,
            "performed_by": h.performed_by,
            "description": h.description,
            "severity": h.severity,
            "created_at": h.created_at.isoformat() if h.created_at else None
        }
        for h in history
    ]


@router.get("/assets/{ip_address}/history", response_model=list[dict])
async def get_asset_history_by_ip(
    ip_address: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get history entries for an asset by IP address.
    
    Retrieves all historical changes tracked for a specific asset
    using its IP address.
    
    Args:
        ip_address: The IP address of the asset
        limit: Maximum number of history entries to return
        
    Returns:
        List[dict]: Array of history entry objects
    """
    # Get asset by IP
    result = await db.execute(
        select(Asset).where(Asset.ip_address == ip_address)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get history entries
    from app.models.asset_history import AssetHistory, get_asset_history
    
    history = get_asset_history(asset.id, limit)
    
    # Convert to response format
    return [
        {
            "id": h.id,
            "asset_id": h.asset_id,
            "change_type": h.change_type,
            "changed_fields": h.changed_fields,
            "old_values": h.old_values,
            "new_values": h.new_values,
            "scan_id": h.scan_id,
            "performed_by": h.performed_by,
            "description": h.description,
            "severity": h.severity,
            "created_at": h.created_at.isoformat() if h.created_at else None
        }
        for h in history
    ]


@router.post("/assets/{asset_id}/history", response_model=dict)
async def create_asset_history_entry(
    asset_id: int,
    change_type: str,
    old_values: dict = None,
    new_values: dict = None,
    changed_fields: list = None,
    scan_id: int = None,
    description: str = None,
    severity: str = None,
    user: User = Depends(require_write_permission),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new history entry for an asset.
    
    Manually records a change to an asset's state. Requires write permissions.
    
    Args:
        asset_id: The unique identifier of the asset
        change_type: Type of change (e.g., os_update, port_change)
        old_values: Dictionary of previous values
        new_values: Dictionary of new values
        changed_fields: List of field names that changed
        scan_id: Optional scan ID that triggered the change
        description: Human-readable description of the change
        severity: Severity level for vulnerability changes
        
    Returns:
        dict: Created history entry confirmation
        
    Raises:
        HTTPException(403): If user lacks write permissions
        HTTPException(404): If asset not found
    """
    # Verify asset exists
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Create history entry
    from app.models.asset_history import add_asset_history
    
    history_entry = await add_asset_history(
        asset_id=asset_id,
        change_type=change_type,
        old_values=old_values or {},
        new_values=new_values or {},
        changed_fields=changed_fields,
        scan_id=scan_id,
        performed_by=user.username if user else "system",
        description=description or f"Manual change: {change_type}",
        severity=severity
    )
    
    return {
        "message": "History entry created",
        "history_id": history_entry.id,
        "change_type": change_type
    }
