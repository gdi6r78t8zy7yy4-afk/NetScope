# NetScope Schemas Module

"""
Pydantic schemas for API request/response validation.
"""

from app.schemas.asset import Asset, AssetCreate, AssetUpdate
from app.schemas.network import Network, NetworkCreate, NetworkUpdate
from app.schemas.scan import Scan, ScanCreate, ScanUpdate, ScanTarget
from app.schemas.vulnerability import (
    VulnerabilityResponse,
    VulnerabilityListResponse,
    CVSSData,
    EPSSData,
    KEVData,
)

__all__ = [
    "Asset",
    "AssetCreate",
    "AssetUpdate",
    "Network",
    "NetworkCreate",
    "NetworkUpdate",
    "Scan",
    "ScanCreate",
    "ScanUpdate",
    "ScanTarget",
    "VulnerabilityResponse",
    "VulnerabilityListResponse",
    "CVSSData",
    "EPSSData",
    "KEVData",
]
