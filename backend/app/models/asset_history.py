# NetScope Asset History Models

"""
Asset history tracking for change monitoring and audit trails.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, func, JSON
from sqlalchemy.orm import relationship

from app.database.base import Base


class ChangeType(str, Enum):
    """Types of asset changes that can be tracked."""

    OS_UPDATE = "os_update"
    PORT_CHANGE = "port_change"
    SERVICE_ADDED = "service_added"
    SERVICE_REMOVED = "service_removed"
    PORT_OPENED = "port_opened"
    PORT_CLOSED = "port_closed"
    HOSTNAME_CHANGE = "hostname_change"
    IP_ADDRESS_CHANGE = "ip_address_change"
    VULNERABILITY_FOUND = "vulnerability_found"
    VULNERABILITY_FIXED = "vulnerability_fixed"
    METADATA_UPDATE = "metadata_update"
    SCAN_COMPLETED = "scan_completed"


class AssetHistory(Base):
    """
    Model for tracking asset changes over time.

    Provides an audit trail of all significant changes to assets,
    including OS updates, port changes, and vulnerability findings.
    """

    __tablename__ = "asset_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Asset reference
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    # Change tracking
    change_type = Column(String(50), nullable=False, index=True)
    changed_fields = Column(JSON, nullable=True)  # Changed field names
    old_values = Column(JSON, nullable=True)  # Previous values
    new_values = Column(JSON, nullable=True)  # New values

    # Context information
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)
    performed_by = Column(String(100), nullable=True)  # User or system
    description = Column(Text, nullable=True)

    # Severity (for vulnerability-related changes)
    severity = Column(String(20), nullable=True)  # critical, high, medium, low

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    asset = relationship("Asset", backref="history_entries")
    scan = relationship("Scan", backref="asset_history")


class AssetChange(Base):
    """
    Detailed asset change record for granular tracking.

    Tracks individual field changes with timestamps and context.
    """

    __tablename__ = "asset_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    # Change details
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    # Context
    change_type = Column(String(50), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)  # For status changes

    # Relationships
    asset = relationship("Asset", backref="changes")
    scan = relationship("Scan", backref="asset_changes")


def create_asset_history_entry(
    asset_id: int,
    change_type: str,
    old_values: dict = None,
    new_values: dict = None,
    changed_fields: list = None,
    scan_id: int = None,
    performed_by: str = "system",
    description: str = None,
    severity: str = None,
) -> AssetHistory:
    """
    Create a new asset history entry.

    Args:
        asset_id: ID of the affected asset
        change_type: Type of change (from ChangeType enum)
        old_values: Dictionary of previous values
        new_values: Dictionary of new values
        changed_fields: List of field names that changed
        scan_id: Optional scan ID that triggered the change
        performed_by: User or system identifier
        description: Human-readable description of the change
        severity: Severity level for vulnerability changes

    Returns:
        AssetHistory: The created history entry
    """
    from app.database import SessionLocal

    entry = AssetHistory(
        asset_id=asset_id,
        change_type=change_type,
        old_values=old_values,
        new_values=new_values,
        changed_fields=changed_fields,
        scan_id=scan_id,
        performed_by=performed_by,
        description=description,
        severity=severity,
    )

    return entry


async def add_asset_history(
    asset_id: int,
    change_type: str,
    old_values: dict = None,
    new_values: dict = None,
    changed_fields: list = None,
    scan_id: int = None,
    performed_by: str = "system",
    description: str = None,
    severity: str = None,
) -> AssetHistory:
    """
    Add a new asset history entry to the database.

    Args:
        asset_id: ID of the affected asset
        change_type: Type of change (from ChangeType enum)
        old_values: Dictionary of previous values
        new_values: Dictionary of new values
        changed_fields: List of field names that changed
        scan_id: Optional scan ID that triggered the change
        performed_by: User or system identifier
        description: Human-readable description of the change
        severity: Severity level for vulnerability changes

    Returns:
        AssetHistory: The created history entry
    """
    from app.database import SessionLocal

    entry = AssetHistory(
        asset_id=asset_id,
        change_type=change_type,
        old_values=old_values or {},
        new_values=new_values or {},
        changed_fields=changed_fields,
        scan_id=scan_id,
        performed_by=performed_by,
        description=description,
        severity=severity,
    )

    async with SessionLocal() as session:
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

    return entry


def get_asset_history(asset_id: int, limit: int = 100) -> list:
    """
    Get history entries for an asset.

    Args:
        asset_id: ID of the asset
        limit: Maximum number of entries to return

    Returns:
        List of AssetHistory entries
    """
    from app.database import SessionLocal

    with SessionLocal() as session:
        history = (
            session.query(AssetHistory)
            .filter(AssetHistory.asset_id == asset_id)
            .order_by(AssetHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    return history


def get_asset_changes(asset_id: int, limit: int = 100) -> list:
    """
    Get detailed change records for an asset.

    Args:
        asset_id: ID of the asset
        limit: Maximum number of entries to return

    Returns:
        List of AssetChange entries
    """
    from app.database import SessionLocal

    with SessionLocal() as session:
        changes = (
            session.query(AssetChange)
            .filter(AssetChange.asset_id == asset_id)
            .order_by(AssetChange.created_at.desc())
            .limit(limit)
            .all()
        )

    return changes
