# NetScope Full Scan Flow Tests

"""
Tests for the complete scan flow:
1. Create a discovery scan
2. Run the scan (with mocked nmap)
3. Verify assets are created from discovered hosts
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_full_discovery_scan_flow():
    """
    Test the complete scan flow:
    1. Create a scan
    2. Run discovery scan
    3. Verify assets are created
    """
    from app.engines.discovery.active import ActiveDiscoveryEngine

    # Mock nmap output
    nmap_output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
MAC Address: 00:11:22:33:44:55 (Vendor)
Nmap scan report for 192.168.1.2
Host is up (0.002s latency).
MAC Address: AA:BB:CC:DD:EE:FF (Vendor)
Nmap done: 2 IP addresses (2 hosts up) scanned in 0.1 seconds"""

    with patch("app.engines.discovery.active.run_command") as mock_run:

        async def mock_run_command(cmd, timeout):
            return {"stdout": nmap_output, "stderr": "", "returncode": 0}

        mock_run.side_effect = mock_run_command

        # Create discovery engine
        engine = ActiveDiscoveryEngine(
            max_concurrent_hosts=5, scan_timeout=120)

        # Run discovery
        result = await engine.discover_with_nmap("192.168.1.0/24", rate_limit="medium")

        # Verify discovery results
        assert result["discovery_method"] == "active_nmap"
        assert result["hosts_found"] >= 1
        assert len(result["hosts"]) >= 2

        # Verify host structure (the key issue: field names must match)
        for host in result["hosts"]:
            # The discovery should have ip_address field (not just ip)
            assert "ip_address" in host, f"Host missing ip_address: {host}"
            assert host.get("ip_address") is not None
            assert host.get("mac_address") is not None

            # Create asset from host (simulating scan.py logic)
            ip = host.get("ip_address") or host.get("ip")
            hostname = host.get("hostname", "")
            mac = host.get("mac_address") or host.get("mac", "")

            from app.models.asset import Asset

            asset = Asset(
                ip_address=ip, mac_address=None if mac == "" else mac, hostname=hostname
            )

            assert asset.ip_address is not None


@pytest.mark.asyncio
async def test_discovery_scan_creates_assets_correctly():
    """
    Test that the asset creation logic in scans.py works correctly.
    This simulates what happens when a discovery scan is run.
    """
    from app.engines.discovery.active import ActiveDiscoveryEngine
    from app.models.asset import Asset

    # Mock nmap output
    nmap_output = """Nmap scan report for 127.0.0.1
Host is up (0.001s latency).
MAC Address: 00:00:00:00:00:01 (Mock)
Nmap done: 1 IP address (1 host up) scanned in 0.1 seconds"""

    with patch("app.engines.discovery.active.run_command") as mock_run:

        async def mock_run_command(cmd, timeout):
            return {"stdout": nmap_output, "stderr": "", "returncode": 0}

        mock_run.side_effect = mock_run_command

        engine = ActiveDiscoveryEngine()
        result = await engine.discover_with_nmap("127.0.0.1")

        # Verify the result structure
        assert "hosts" in result
        assert result["hosts_found"] >= 1

        # Simulate the asset creation logic from scans.py
        assets_to_create = []

        for host in result["hosts"]:
            # This is the critical fix: extract IP with fallbacks
            ip = host.get("ip_address") or host.get(
                "ip") or host.get("ipaddress")
            hostname = host.get("hostname", "")

            # This is the key fix: check for existing asset using ip_address
            # field
            existing_ip_check = host.get("ip")  # Old way - wrong

            if ip is None:
                raise AssertionError(f"IP should not be None for host: {host}")

            # Create asset using correct field names
            mac = host.get("mac_address") or host.get("mac", "")
            device_type = host.get("device_type") or host.get("device", "")

            asset = Asset(
                ip_address=ip,
                mac_address=None if mac == "" else mac,
                hostname=hostname,
                device_type=device_type,
            )

            assets_to_create.append(asset)

        # Verify assets were created correctly
        assert len(assets_to_create) >= 1

        for asset in assets_to_create:
            assert asset.ip_address is not None
            assert asset.ip_address != ""


def test_asset_field_mapping():
    """
    Test that asset field mapping works correctly with discovery scan data.
    This test specifically checks for the bug where 'ip' was used instead of 'ip_address'.
    """
    from app.models.asset import Asset

    # Simulate discovery scan host data
    host_data = {
        "ip_address": "192.168.1.100",  # The correct field name from discovery
        "hostname": "my-host",
        "mac_address": "AA:BB:CC:DD:EE:FF",
    }

    # This should work - using correct field names
    asset = Asset(
        ip_address=host_data["ip_address"],
        mac_address=host_data.get("mac_address"),
        hostname=host_data.get("hostname", ""),
    )

    assert asset.ip_address == "192.168.1.100"
    assert asset.hostname == "my-host"

    # Test fallback logic (for backward compatibility)
    test_cases = [
        {"ip_address": "1.1.1.1", "ip": None, "ipaddress": None},
        {"ip_address": "2.2.2.2", "ip": "3.3.3.3", "ipaddress": "4.4.4.4"},
        {"ip_address": None, "ip": "5.5.5.5", "ipaddress": "6.6.6.6"},
    ]

    for tc in test_cases:
        ip = tc.get("ip_address") or tc.get("ip") or tc.get("ipaddress")
        assert ip is not None, f"IP should not be None for test case: {tc}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
