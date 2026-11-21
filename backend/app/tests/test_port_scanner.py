# NetScope Port Scanner Integration Tests

"""
Tests for port scanning functionality.
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


def test_scan_port_single():
    """Test single port scanning."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    # Valid port
    assert scanner.timeout == 5
    assert len(scanner.COMMON_PORTS) > 0


def test_scan_port_range():
    """Test port range scanning."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    # Test common ports
    assert scanner.COMMON_PORTS == [
        21,
        22,
        23,
        25,
        53,
        80,
        110,
        143,
        443,
        445,
        993,
        995,
        1433,
        1521,
        3306,
        3389,
        5432,
        5900,
        8080,
        8443,
    ]


def test_scan_port_validation():
    """Test port number validation."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    # Test port range validation
    from app.core.validators import validate_port_range

    assert validate_port_range(1, 65535)[0] is True
    assert validate_port_range(80, 443)[0] is True
    assert validate_port_range(1, 70000)[0] is False
    assert validate_port_range(-1, 100)[0] is False


@pytest.mark.asyncio
async def test_scan_single_port():
    """Test scanning a single port."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    # Test port scan output parsing
    output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1

Service detection performed. Please report any incorrect results at https://nmap.org/missing/ ."""

    result = scanner._parse_scan_output(output, "192.168.1.1", 22)

    assert result["ip_address"] == "192.168.1.1"
    assert result["port"] == 22
    assert "state" in result


@pytest.mark.asyncio
async def test_scan_multiple_ports():
    """Test scanning multiple ports."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).

PORT   STATE SERVICE
21/tcp closed ftp
22/tcp open    ssh
80/tcp open    http

Nmap done: 1 IP address (1 host up) scanned in 0.1 seconds"""

    ports = [21, 22, 80]
    result = scanner._parse_multi_port_output(output, "192.168.1.1", ports)

    assert result["ip_address"] == "192.168.1.1"
    assert result["ports_scanned"] == 3


@pytest.mark.asyncio
async def test_scan_port_range_function():
    """Test port range scanning."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    output = """Nmap scan report for 192.168.1.1
Host is up (0.001s latency).

PORT     STATE SERVICE
20-22/tcp open  ftp|ssh
80/tcp   open  http

Nmap done: 1 IP address (1 host up) scanned in 0.1 seconds"""

    result = scanner._parse_range_output(output, "192.168.1.1", 20, 80)

    assert result["ip_address"] == "192.168.1.1"
    assert result["port_range"] == "20-80"


def test_scan_common_ports():
    """Test common ports scan."""
    from app.engines.port_scanner.nmap_engine import NmapPortScanner

    scanner = NmapPortScanner(timeout=5)

    ports = scanner.COMMON_PORTS
    assert 22 in ports  # SSH
    assert 80 in ports  # HTTP
    assert 443 in ports  # HTTPS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
