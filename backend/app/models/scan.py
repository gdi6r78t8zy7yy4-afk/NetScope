# NetScope Scan Models

"""
Scan and scan target models for tracking scanning operations.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Scan(Base):
    """Represents a scan operation."""
    
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    scan_type = Column(String(50), nullable=False)  # discovery, port_scan, vulnerability
    status = Column(String(20), default="pending")  # pending, running, completed, cancelled
    progress = Column(Integer, default=0)
    
    # Scan configuration
    target_cidr = Column(String(100), nullable=False)
    rate_limit = Column(String(20), default="medium")
    ports = Column(Text, nullable=True)  # JSON list of ports
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    hosts_found = Column(Integer, default=0)
    ports_found = Column(Integer, default=0)
    services_found = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ScanTarget(Base):
    """Represents a target within a scan."""
    
    __tablename__ = "scan_targets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    hostname = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, scanning, completed, failed
    progress = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ScanEvidence(Base):
    """Stores raw scan evidence for reproducibility."""
    
    __tablename__ = "scan_evidence"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)  # Link to scan
    evidence_type = Column(String(50), nullable=False)  # nmap_xml, arp_scan, etc.
    data = Column(Text, nullable=False)  # Raw scan output
    evidence_metadata = Column(Text, nullable=True)  # JSON metadata
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# Re-export for convenience
__all__ = ['Scan', 'ScanTarget', 'ScanEvidence']
