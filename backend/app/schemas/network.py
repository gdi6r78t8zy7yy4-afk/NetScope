# NetScope Network Schemas

"""
Pydantic schemas for network-related API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NetworkBase(BaseModel):
    """Base network schema."""
    
    name: str
    cidr: str
    description: Optional[str] = None
    enabled: bool = True
    scan_priority: int = 1
    rate_limit: str = "medium"


class NetworkCreate(NetworkBase):
    """Schema for creating a network."""
    
    pass


class NetworkUpdate(BaseModel):
    """Schema for updating a network."""
    
    name: Optional[str] = None
    cidr: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    scan_priority: Optional[int] = None
    rate_limit: Optional[str] = None


class Network(NetworkBase):
    """Schema for network response."""
    
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubnetBase(BaseModel):
    """Base subnet schema."""
    
    name: str
    cidr: str
    network_id: int


class SubnetCreate(SubnetBase):
    """Schema for creating a subnet."""
    
    pass


class SubnetUpdate(BaseModel):
    """Schema for updating a subnet."""
    
    name: Optional[str] = None
    cidr: Optional[str] = None


class Subnet(SubnetBase):
    """Schema for subnet response."""
    
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScanTargetBase(BaseModel):
    """Base scan target schema."""
    
    ip_address: str
    hostname: Optional[str] = None


class ScanTargetCreate(ScanTargetBase):
    """Schema for creating a scan target."""
    
    scan_id: int


class ScanTarget(ScanTargetBase):
    """Schema for scan target response."""
    
    id: int
    status: str = "pending"
    progress: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
