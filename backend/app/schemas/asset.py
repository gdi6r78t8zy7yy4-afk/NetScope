# NetScope Asset Schemas

"""
Pydantic schemas for asset-related API requests and responses.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, Field

from app.core.validators import validate_ipv4, validate_cidr


class AssetBase(BaseModel):
    """Base asset schema."""
    
    ip_address: str
    
    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        if not validate_ipv4(v):
            # Also allow CIDR notation for network ranges
            if "/" in v and validate_cidr(v):
                return v
            raise ValueError(f"Invalid IP address format: {v}")
        return v
    
    mac_address: Optional[str] = Field(
        None,
        description="MAC address in format XX:XX:XX:XX:XX:XX"
    )
    
    @field_validator("mac_address")
    @classmethod
    def validate_mac_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate MAC address format."""
        if v is None:
            return v
        
        # Validate MAC address format (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)
        import re
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not re.match(mac_pattern, v):
            raise ValueError(f"Invalid MAC address format: {v}")
        return v
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    confidence_level: str = "unknown"


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""
    
    subnet_id: Optional[int] = None
    scan_evidence_id: Optional[int] = None


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""
    
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    device_type: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    vendor: Optional[str] = None
    confidence_level: Optional[str] = None


class Asset(AssetBase):
    """Schema for asset response."""
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    open_port_count: int = 0
    vulnerability_count: int = 0
    kev_count: int = 0
    
    class Config:
        from_attributes = True


class NetworkInterfaceBase(BaseModel):
    """Base network interface schema."""
    
    name: str
    mac_address: Optional[str] = None
    ip_address: str
    
    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        if not validate_ipv4(v):
            raise ValueError(f"Invalid IP address format: {v}")
        return v
    netmask: str = "255.255.255.0"
    gateway: Optional[str] = None
    interface_type: str = "ethernet"


class NetworkInterfaceCreate(NetworkInterfaceBase):
    """Schema for creating a network interface."""
    
    asset_id: int


class NetworkInterface(NetworkInterfaceBase):
    """Schema for network interface response."""
    
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PortBase(BaseModel):
    """Base port schema."""
    
    port_number: int
    protocol: str = "tcp"
    state: str = "unknown"
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    banner: Optional[str] = None
    confidence_level: str = "unknown"


class PortCreate(PortBase):
    """Schema for creating a port."""
    
    asset_id: int
    interface_id: Optional[int] = None


class Port(PortBase):
    """Schema for port response."""
    
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PortScanResult(BaseModel):
    """Schema for port scan results."""
    
    ip_address: str
    ports: List[Port]
    open_port_count: int = 0
    closed_port_count: int = 0
    filtered_port_count: int = 0


class HostProfileBase(BaseModel):
    """Base host profile schema."""
    
    boot_time: Optional[str] = None
    uptime: Optional[int] = None
    open_ports_count: int = 0
    services_count: int = 0
    network_interfaces_count: int = 1
    os_fingerprint_confidence: str = "unknown"
    os_gen: Optional[str] = None
    os_type: Optional[str] = None
    mac_vendor: Optional[str] = None
    hops_count: Optional[int] = None


class HostProfileCreate(HostProfileBase):
    """Schema for creating a host profile."""
    
    asset_id: int


class HostProfile(HostProfileBase):
    """Schema for host profile response."""
    
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
