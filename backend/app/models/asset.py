# NetScope Asset Models

"""
Asset and network interface models.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Asset(Base):
    """Represents a discovered network asset (host)."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    mac_address = Column(String(17), nullable=True, index=True)
    hostname = Column(String(255), nullable=True)
    device_type = Column(String(100), nullable=True)
    operating_system = Column(String(255), nullable=True)
    os_version = Column(String(100), nullable=True)
    vendor = Column(String(255), nullable=True)
    confidence_level = Column(String(20), default="unknown")

    # Scan tracking for auto-cleanup
    last_seen_scan_id = Column(Integer, nullable=True)
    consecutive_absent_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    vulnerabilities = relationship(
        "AssetVulnerability",
        back_populates="asset")
    ports = relationship("Port", back_populates="asset")


class NetworkInterface(Base):
    """Represents a network interface on an asset."""

    __tablename__ = "network_interfaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    mac_address = Column(String(17), nullable=True, unique=True)
    ip_address = Column(String(45), nullable=False)
    netmask = Column(String(10), default="255.255.255.0")
    gateway = Column(String(45), nullable=True)
    interface_type = Column(String(20), default="ethernet")

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Port(Base):
    """Represents a scanned port on an asset."""

    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    port_number = Column(Integer, nullable=False)
    protocol = Column(String(10), default="tcp")
    state = Column(String(20), default="unknown")  # open, closed, filtered
    service_name = Column(String(100), nullable=True)
    product = Column(String(255), nullable=True)
    version = Column(String(100), nullable=True)
    banner = Column(Text, nullable=True)
    confidence_level = Column(String(20), default="unknown")

    # Relationships
    asset = relationship("Asset", back_populates="ports")

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class HostProfile(Base):
    """Represents a detailed host profile."""

    __tablename__ = "host_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.id"),
        nullable=False,
        unique=True)
    boot_time = Column(String(50), nullable=True)
    uptime = Column(Integer, nullable=True)  # in seconds
    open_ports_count = Column(Integer, default=0)
    services_count = Column(Integer, default=0)
    network_interfaces_count = Column(Integer, default=1)

    # OS fingerprinting details
    os_fingerprint_confidence = Column(String(20), default="unknown")
    os_gen = Column(String(100), nullable=True)
    os_type = Column(String(50), nullable=True)

    # Network details
    mac_vendor = Column(String(255), nullable=True)
    hops_count = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class AssetVulnerability(Base):
    """Association table for asset-vulnerability relationships."""

    __tablename__ = "asset_vulnerabilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    vulnerability_id = Column(
        Integer, ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False
    )
    confidence = Column(
        String(20), default="potential"
    )  # confirmed, potential, unverified
    evidence = Column(Text, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="vulnerabilities")
    # Note: Vulnerability model doesn't have asset_vulnerabilities relationship

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# Re-export for convenience
__all__ = [
    "Asset",
    "NetworkInterface",
    "Port",
    "HostProfile",
    "AssetVulnerability"]
