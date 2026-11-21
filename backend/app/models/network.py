# NetScope Network Models

"""
Network and subnet models for IP address management.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from app.database.base import Base


class Network(Base):
    """Represents a configured network for scanning."""

    __tablename__ = "networks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    cidr = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)

    # Scanning configuration
    # Higher number = higher priority
    scan_priority = Column(Integer, default=1)
    rate_limit = Column(String(20), default="medium")

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Network(name={self.name}, cidr={self.cidr})>"


class Subnet(Base):
    """Represents a subnet within a network."""

    __tablename__ = "subnets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    cidr = Column(String(50), nullable=False, index=True)
    network_id = Column(Integer, ForeignKey("networks.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Subnet(name={self.name}, cidr={self.cidr})>"


# Re-export for convenience
__all__ = ["Network", "Subnet"]
