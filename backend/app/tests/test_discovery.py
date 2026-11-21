# NetScope Discovery Engine Integration Tests

"""
Tests for network discovery engines.
"""

import pytest
from unittest.mock import patch


class MockProcess:
    """Mock subprocess for testing."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return (self._stdout.encode(), self._stderr.encode())


@pytest.mark.asyncio
async def test_passive_discovery_arp_table():
    """Test passive ARP table discovery."""
    from app.engines.discovery.passive import PassiveDiscoveryEngine

    engine = PassiveDiscoveryEngine()

    stdout_content = """router (192.168.1.1) at 00:11:22:33:44:55 [ether] on en0
host1 (192.168.1.10) at aa:bb:cc:dd:ee:ff [ether] on en0"""

    with patch("asyncio.create_subprocess_exec") as mock_create:

        class MockProc:
            returncode = 0

            async def communicate(self):
                return (stdout_content.encode(), b"")

        mock_create.return_value = MockProc()

        result = await engine.discover_from_arp_table()

        assert isinstance(result, list)
        assert len(result) >= 2

        first_host = result[0]
        assert "ip_address" in first_host
        assert "mac_address" in first_host


@pytest.mark.asyncio
async def test_active_discovery_nmap():
    """Test active Nmap discovery."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine(scan_timeout=5)

    stdout_content = """Nmap scan report for 192.168.1.1
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
                return (stdout_content.encode(), b"")

        mock_create.return_value = MockProc()

        result = await engine.discover_with_nmap("192.168.1.0/24")

        assert result["discovery_method"] == "active_nmap"
        assert result["hosts_found"] >= 1


def test_discover_interfaces():
    """Test interface discovery."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine()

    output = """Device: en0
Hardware Port: Ethernet
Ethernet Address: 12:34:56:78:90:AB
Status: active

Device: en1
Hardware Port: Wi-Fi
Ethernet Address: BA:09:87:65:43:21
Status: inactive"""

    interfaces = engine._parse_interfaces_output(output)

    assert len(interfaces) >= 2
    assert interfaces[0]["interface"] == "en0"
    # MAC address comes from "Ethernet Address:" field
    assert interfaces[0]["mac_address"] == "12:34:56:78:90:AB"
    assert interfaces[0]["status"] == "active"


def test_passive_vs_active_separation():
    """Test that passive and active discoveries are properly separated."""
    from app.engines.discovery.passive import PassiveDiscoveryEngine
    from app.engines.discovery.active import ActiveDiscoveryEngine

    passive = PassiveDiscoveryEngine()
    active = ActiveDiscoveryEngine()

    assert hasattr(passive, "discover_from_arp_table")
    assert hasattr(active, "discover_with_nmap")
    assert not hasattr(passive, "discover_with_nmap")
    assert not hasattr(active, "discover_from_arp_table")


def test_asset_deduplication():
    """Test asset deduplication during discovery."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine()

    hosts = [
        {"ip_address": "192.168.1.1", "hostname": "router"},
        {"ip_address": "192.168.1.10", "hostname": "server"},
        {"ip_address": "192.168.1.1", "hostname": "router-duplicate"},
    ]

    unique_hosts = []
    seen_ips = set()

    for host in hosts:
        ip = host.get("ip_address")
        if ip and ip not in seen_ips:
            unique_hosts.append(host)
            seen_ips.add(ip)

    assert len(unique_hosts) == 2
    assert unique_hosts[0]["ip_address"] == "192.168.1.1"
    assert unique_hosts[1]["ip_address"] == "192.168.1.10"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
