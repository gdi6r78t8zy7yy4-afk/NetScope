# NetScope Scan Schemas

"""
Pydantic schemas for scan-related API requests and responses.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, Field

from app.core.validators import validate_cidr, parse_and_validate_ports


class ScanBase(BaseModel):
    """Base scan schema."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Name of the scan"
    )
    scan_type: str = Field(
        ..., description="Type of scan (discovery, port_scan, vulnerability)"
    )
    status: str = Field(
        default="pending",
        description="Current status of the scan")
    progress: int = Field(
        default=0, ge=0, le=100, description="Scan progress percentage"
    )
    target_cidr: str = Field(..., description="Target network in CIDR format")
    rate_limit: str = Field(
        default="medium",
        description="Scan speed preset (slow, medium, fast, aggressive)",
    )
    ports: Optional[str] = Field(
        None, description="Port specification (comma-separated or range)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate scan name."""
        if v is not None and len(v) > 255:
            raise ValueError("Scan name must be at most 255 characters")
        return v

    @field_validator("target_cidr")
    @classmethod
    def validate_target_cidr(cls, v: str) -> str:
        """Validate target CIDR format."""
        if not validate_cidr(v):
            raise ValueError(f"Invalid CIDR format: {v}")
        return v

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit(cls, v: str) -> str:
        """Validate rate limit preset."""
        valid_presets = ["slow", "medium", "fast", "aggressive"]
        if v not in valid_presets:
            raise ValueError(f"Rate limit must be one of: {valid_presets}")
        return v

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: int) -> int:
        """Validate progress is between 0-100."""
        if v < 0 or v > 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: Optional[str]) -> Optional[str]:
        """Validate ports format."""
        if v is None:
            return v

        valid, _, message = parse_and_validate_ports(v)
        if not valid:
            raise ValueError(f"Invalid ports format: {message}")
        return v


class ScanCreate(ScanBase):
    """Schema for creating a new scan."""

    pass


class ScanUpdate(BaseModel):
    """Schema for updating a scan."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="New scan status")
    progress: Optional[int] = Field(None, ge=0, le=100)
    target_cidr: Optional[str] = Field(None, description="Updated target CIDR")
    rate_limit: Optional[str] = Field(
        None, description="Updated rate limit preset")


class Scan(ScanBase):
    """Schema for scan response."""

    id: int = Field(..., description="Unique identifier of the scan")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(
        None, description="Start time of the scan")
    completed_at: Optional[datetime] = Field(
        None, description="Completion timestamp")

    hosts_found: int = Field(
        default=0,
        ge=0,
        description="Number of hosts discovered")
    ports_found: int = Field(
        default=0,
        ge=0,
        description="Number of ports found")
    services_found: int = Field(
        default=0, ge=0, description="Number of services identified"
    )


class ScanTarget(BaseModel):
    """Schema for scan target response."""

    id: int = Field(..., description="Unique identifier")
    ip_address: str = Field(..., description="IP address of the target")
    hostname: Optional[str] = Field(None, description="Hostname of the target")
    status: str = Field(default="pending", description="Target scan status")
    progress: int = Field(default=0, ge=0, le=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    open_ports: int = Field(default=0, ge=0)
    closed_ports: int = Field(default=0, ge=0)
    filtered_ports: int = Field(default=0, ge=0)


class ScanEvidenceBase(BaseModel):
    """Base scan evidence schema."""

    evidence_type: str = Field(
        ..., description="Type of evidence (nmap_raw, nmap_parsed)"
    )
    data: str = Field(..., description="Raw scan output")
    metadata: Optional[str] = Field(None, description="Additional metadata")


class ScanEvidenceCreate(ScanEvidenceBase):
    """Schema for creating scan evidence."""

    scan_id: int = Field(..., ge=1, description="ID of the associated scan")
    asset_id: Optional[int] = Field(
        None, ge=1, description="ID of the associated asset"
    )


class ScanEvidence(ScanEvidenceBase):
    """Schema for scan evidence response."""

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")


class ScanScheduleBase(BaseModel):
    """Base scan schedule schema."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the schedule"
    )
    cron_pattern: str = Field(..., description="Cron-like scheduling pattern")
    scan_type: str = Field(
        default="port_scan",
        description="Type of scan to schedule")
    target_cidr: str = Field(
        default="192.168.0.0/16", description="Default target CIDR"
    )
    enabled: bool = Field(
        default=True,
        description="Whether schedule is active")
    priority: int = Field(
        default=0, ge=-10, le=10, description="Priority level (-10 to 10)"
    )
    rate_limit: str = Field(default="medium", description="Scan speed preset")

    @field_validator("name")
    @classmethod
    def validate_schedule_name(cls, v: str) -> str:
        """Validate schedule name."""
        if len(v) > 255:
            raise ValueError("Schedule name must be at most 255 characters")
        return v

    @field_validator("cron_pattern")
    @classmethod
    def validate_cron_pattern(cls, v: str) -> str:
        """Validate cron pattern format."""
        # Basic validation for cron patterns
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Cron pattern must have exactly 5 fields")
        return v

    @field_validator("rate_limit")
    @classmethod
    def validate_schedule_rate_limit(cls, v: str) -> str:
        """Validate rate limit preset."""
        valid_presets = ["slow", "medium", "fast", "aggressive"]
        if v not in valid_presets:
            raise ValueError(f"Rate limit must be one of: {valid_presets}")
        return v


class ScanScheduleCreate(ScanScheduleBase):
    """Schema for creating a new schedule."""

    pass


class ScanSchedule(ScanScheduleBase):
    """Schema for scan schedule response."""

    id: int = Field(..., description="Unique identifier")
    created_at: Optional[datetime] = Field(
        None, description="Creation timestamp")


class ScanScheduleList(BaseModel):
    """Schema for schedule list response."""

    total: int = Field(..., description="Total number of schedules")
    items: List[dict] = Field(..., description="List of schedule items")


class PortScanRequest(BaseModel):
    """Request schema for port scanning."""

    target_ip: str = Field(..., description="Target IP address to scan")
    ports: Optional[List[int]] = Field(
        None, description="List of port numbers to scan")
    port_range: Optional[str] = Field(
        None, description="Port range specification")
    scan_type: str = Field(
        default="syn",
        description="Scan type (syn, connect, udp)")
    rate_limit: str = Field(default="medium", description="Scan speed preset")
    timeout_seconds: int = Field(
        default=60, ge=1, le=3600, description="Scan timeout in seconds"
    )

    @field_validator("target_ip")
    @classmethod
    def validate_target_ip(cls, v: str) -> str:
        """Validate target IP address."""
        from app.core.validators import validate_ipv4, validate_ipv6

        if not (validate_ipv4(v) or validate_ipv6(v)):
            raise ValueError(f"Invalid IP address format: {v}")
        return v

    @field_validator("scan_type")
    @classmethod
    def validate_scan_type(cls, v: str) -> str:
        """Validate scan type."""
        valid_types = ["syn", "connect", "udp"]
        if v not in valid_types:
            raise ValueError(f"Scan type must be one of: {valid_types}")
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if v < 1 or v > 3600:
            raise ValueError("Timeout must be between 1 and 3600 seconds")
        return v


class PortScanResponse(BaseModel):
    """Response schema for port scan."""

    scan_id: int = Field(..., description="ID of the created scan")
    target_ip: str = Field(..., description="Target IP address")
    status: str = Field(default="pending", description="Scan status")
    progress: int = Field(default=0, ge=0, le=100)
    ports_scanned: int = Field(default=0, ge=0)
    open_ports: List[int] = Field(default_factory=list)
    closed_ports: List[int] = Field(default_factory=list)
    filtered_ports: List[int] = Field(default_factory=list)


class ScanResult(BaseModel):
    """Schema for scan result."""

    scan_id: int = Field(..., description="ID of the scan")
    target_cidr: str = Field(..., description="Target CIDR range")
    status: str = Field(default="pending", description="Scan status")
    progress: int = Field(default=0, ge=0, le=100)
    hosts_found: int = Field(default=0, ge=0)
    ports_found: int = Field(default=0, ge=0)
    services_found: int = Field(default=0, ge=0)
    scan_type: str = Field(
        default="port_scan",
        description="Type of scan performed")


class ScanSummary(BaseModel):
    """Schema for scan summary."""

    total_hosts: int = Field(..., ge=0, description="Total hosts scanned")
    hosts_up: int = Field(..., ge=0, description="Hosts detected as up")
    hosts_down: int = Field(..., ge=0, description="Hosts detected as down")
    host_success_rate: float = Field(
        ..., ge=0.0, le=100.0, description="Success rate percentage"
    )
    unique_ports: List[int] = Field(...,
                                    description="List of unique ports found")
    total_findings: int = Field(..., ge=0,
                                description="Total vulnerability findings")
