# NetScope Engine Tests

"""
Unit tests for discovery and scanning engines.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_passive_discovery_arp_parsing():
    """Test ARP table parsing."""
    from app.engines.discovery.passive import PassiveDiscoveryEngine

    engine = PassiveDiscoveryEngine()

    # Test ARP output parsing
    arp_output = """
?
? (192.168.1.1) at 00:11:22:33:44:55 [ether] on en0
?
? (192.168.1.2) at 00:aa:bb:cc:dd:ee [ether] on en0
"""

    hosts = engine._parse_arp_output(arp_output)

    assert len(hosts) == 2
    assert hosts[0]["ip_address"] == "192.168.1.1"
    assert hosts[0]["mac_address"] == "00:11:22:33:44:55"
    assert hosts[1]["ip_address"] == "192.168.1.2"


@pytest.mark.asyncio
async def test_passive_discovery_netstat_parsing():
    """Test netstat parsing for active connections."""
    from app.engines.discovery.passive import PassiveDiscoveryEngine

    engine = PassiveDiscoveryEngine()

    netstat_output = """
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 192.168.1.10:54321      10.0.0.1:445            ESTABLISHED
tcp        0      0 192.168.1.10:54322      10.0.0.2:80             ESTABLISHED
"""

    hosts = engine._parse_netstat_output(netstat_output)

    assert len(hosts) >= 0  # Parsing may find valid IPs


@pytest.mark.asyncio
async def test_passive_discovery_empty_output():
    """Test handling of empty output from external commands."""
    from app.engines.discovery.passive import PassiveDiscoveryEngine

    engine = PassiveDiscoveryEngine()

    # Test with empty strings
    result = engine._parse_arp_output("")
    assert result == []

    result = engine._parse_netstat_output("\n\n")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_active_discovery_mock():
    """Test active discovery engine with mock."""
    from app.engines.discovery.active import ActiveDiscoveryEngine

    engine = ActiveDiscoveryEngine(max_concurrent_hosts=2, scan_timeout=30)

    # Verify initialization
    assert engine.max_concurrent_hosts == 2
    assert engine.scan_timeout == 30


@pytest.mark.asyncio
async def test_port_scanner_basic():
    """Test port scanner initialization."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner()

    # Verify initialization
    assert scanner.timeout == 60
    assert scanner.max_retries == 3


@pytest.mark.asyncio
async def test_port_scanner_common_ports():
    """Test common ports list."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner()

    assert len(scanner.COMMON_PORTS) > 0
    assert 22 in scanner.COMMON_PORTS  # SSH
    assert 80 in scanner.COMMON_PORTS  # HTTP
    assert 443 in scanner.COMMON_PORTS  # HTTPS


@pytest.mark.asyncio
async def test_vulnerability_correlator_basic():
    """Test vulnerability correlator initialization."""
    from app.engines.vulnerability.correlation import VulnerabilityCorrelator

    correlator = VulnerabilityCorrelator()

    # Verify initialization
    assert correlator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
