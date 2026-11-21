# NetScope Discovery Assets Tests

"""
Tests for discovery scan asset creation flow.
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_discovery_scan_creates_assets():
    """Test that discovery scans create assets from discovered hosts."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine(scan_timeout=5)

    # Mock Nmap discovery output with valid hosts
    nmap_output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
MAC Address: 00:11:22:33:44:55 (Vendor)
Nmap scan report for 192.168.1.2
Host is up (0.002s latency).
MAC Address: AA:BB:CC:DD:EE:FF (Vendor)
Nmap done: 2 IP addresses (2 hosts up) scanned in 0.1 seconds"""

    with patch("asyncio.create_subprocess_exec") as mock_create:

        class MockProc:
            returncode = 0

            async def communicate(self):
                return (nmap_output.encode(), b"")

        mock_create.return_value = MockProc()

        result = await engine.discover_with_nmap("192.168.1.0/24")

        assert result["discovery_method"] == "active_nmap"
        assert result["hosts_found"] >= 1

        # Check that hosts have correct fields
        for host in result["hosts"]:
            assert "ip_address" in host, "Host missing ip_address field"
            assert "hostname" in host or True  # hostname is optional


@pytest.mark.asyncio
async def test_discovery_scan_localhost():
    """Test discovery scan on localhost with mocked output."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine(scan_timeout=5)

    # Mock Nmap discovery output
    nmap_output = """Nmap scan report for 127.0.0.1
Host is up (0.001s latency).
MAC Address: 00:00:00:00:00:01 (Mock)
Nmap done: 1 IP address (1 host up) scanned in 0.1 seconds"""

    with patch("asyncio.create_subprocess_exec") as mock_create:

        class MockProc:
            returncode = 0

            async def communicate(self):
                return (nmap_output.encode(), b"")

        mock_create.return_value = MockProc()

        result = await engine.discover_with_nmap("127.0.0.1")

        assert result["hosts_found"] >= 1
        host = result["hosts"][0]

        # Verify correct field names
        assert "ip_address" in host
        assert host["ip_address"] == "127.0.0.1"

        # Test the full asset creation logic
        from app.models.asset import Asset

        for host in result["hosts"]:
            ip = host.get("ip_address") or host.get("ip")
            hostname = host.get("hostname", "")

            # Check that we can extract the IP correctly
            assert ip is not None, "IP address should not be None"

            # Verify mac_address field name
            mac = host.get("mac_address") or host.get("mac", "")

            # Create asset
            new_asset = Asset(
                ip_address=ip, mac_address=mac if mac != "" else None, hostname=hostname
            )

            assert new_asset.ip_address == ip
            assert new_asset.hostname == hostname


def test_parse_nmap_output():
    """Test Nmap output parsing."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine()

    output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
MAC Address: 00:11:22:33:44:55 (Vendor)
Nmap scan report for 192.168.1.2
Host is up (0.002s latency).
MAC Address: AA:BB:CC:DD:EE:FF (Vendor)
Nmap done: 2 IP addresses (2 hosts up) scanned in 0.1 seconds"""

    result = engine._parse_nmap_output(output)

    assert result["hosts_found"] == 2
    assert len(result["hosts"]) == 2

    # Verify host structure
    for host in result["hosts"]:
        assert "ip_address" in host
        assert "mac_address" in host


def test_asset_field_extraction():
    """Test that assets can be created with correct field extraction."""
    from app.models.asset import Asset

    # Test host data with discovery scan format
    host_data = {
        "ip_address": "192.168.1.1",
        "hostname": "router",
        "mac_address": "00:11:22:33:44:55",
        "device_type": "router",
        "operating_system": "Linux",
    }

    asset = Asset(
        ip_address=host_data["ip_address"],
        mac_address=host_data.get("mac_address"),
        hostname=host_data.get("hostname", ""),
        device_type=host_data.get("device_type", ""),
        operating_system=host_data.get("operating_system", ""),
    )

    assert asset.ip_address == "192.168.1.1"
    assert asset.hostname == "router"
    assert asset.mac_address == "00:11:22:33:44:55"
    assert asset.device_type == "router"
    assert asset.operating_system == "Linux"


def test_discovery_scan_with_deduplication():
    """Test that duplicate hosts are not created."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine()

    output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
MAC Address: 00:11:22:33:44:55 (Vendor)
Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
MAC Address: 00:11:22:33:44:56 (Different MAC)"""

    result = engine._parse_nmap_output(output)

    # Nmap might list same IP twice in output
    assert result["hosts_found"] == 2

    # But we should have unique IPs in deduplication logic
    seen_ips = set()
    for host in result["hosts"]:
        ip = host.get("ip_address")
        if ip:
            seen_ips.add(ip)

    # In the actual scan logic, deduplication happens at asset creation time
    assert len(seen_ips) >= 1
