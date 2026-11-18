# NetScope Tests Package

"""
Test suite for the application.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Test fixtures and helpers


def create_mock_asset(ip_address: str = "192.168.1.1", **kwargs) -> dict:
    """Create a mock asset dictionary."""
    return {
        "id": 1,
        "ip_address": ip_address,
        "mac_address": kwargs.get("mac_address", "00:11:22:33:44:55"),
        "hostname": kwargs.get("hostname", "test-host"),
        "device_type": kwargs.get("device_type", "unknown"),
        "created_at": kwargs.get("created_at", "2024-01-01T00:00:00Z"),
        "updated_at": kwargs.get("updated_at", "2024-01-01T00:00:00Z"),
    }


def create_mock_vulnerability(cve_id: str = "CVE-2024-1234", **kwargs) -> dict:
    """Create a mock vulnerability dictionary."""
    return {
        "cve_id": cve_id,
        "description": kwargs.get("description", "Sample vulnerability"),
        "cvss_score": kwargs.get("cvss_score", 7.5),
        "severity": kwargs.get("severity", "high"),
    }


class AsyncMockMocker:
    """Helper for async mocking."""
    
    @staticmethod
    def create_mock_session():
        """Create a mock database session."""
        session = AsyncMock()
        
        # Setup common methods
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        return session


# Export fixtures
__all__ = [
    "create_mock_asset",
    "create_mock_vulnerability",
    "AsyncMockMocker",
]
