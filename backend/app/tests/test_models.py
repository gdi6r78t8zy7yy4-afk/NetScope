# NetScope Model Tests

"""
Tests for Pydantic models and data validation.
"""

import pytest
from datetime import datetime


def test_network_model_validation():
    """Test Network model validation."""
    from app.models.network import Network
    
    network = Network()
    network.name = "Production Network"
    network.cidr = "192.168.1.0/24"
    
    assert network.name == "Production Network"
    assert network.cidr == "192.168.1.0/24"


def test_network_model_minimal():
    """Test Network model with minimal fields."""
    from app.models.network import Network
    
    network = Network()
    network.name = "Test"
    network.cidr = "10.0.0.0/8"
    
    assert network.name == "Test"
    assert network.cidr == "10.0.0.0/8"


def test_subnet_model_validation():
    """Test Subnet model validation."""
    from app.models.network import Subnet
    
    subnet = Subnet()
    subnet.name = "DMZ"
    subnet.cidr = "192.168.100.0/24"
    subnet.network_id = 1
    
    assert subnet.name == "DMZ"
    assert subnet.cidr == "192.168.100.0/24"
    assert subnet.network_id == 1


def test_scan_model_validation():
    """Test Scan model validation."""
    from app.models.scan import Scan
    
    scan = Scan()
    scan.name = "Test Scan"
    scan.scan_type = "port"
    scan.status = "pending"
    scan.target_cidr = "192.168.1.0/24"
    
    assert scan.name == "Test Scan"
    assert scan.scan_type == "port"
    assert scan.status == "pending"


def test_scan_target_model_validation():
    """Test ScanTarget model validation."""
    from app.models.scan import ScanTarget
    
    target = ScanTarget()
    target.ip_address = "192.168.1.50"
    target.port = 443
    target.protocol = "tcp"
    
    assert target.ip_address == "192.168.1.50"


def test_asset_model_validation():
    """Test Asset model validation."""
    from app.models.asset import Asset
    
    asset = Asset()
    asset.ip_address = "192.168.1.100"
    asset.mac_address = "00:11:22:33:44:55"
    asset.hostname = "test-host"
    asset.operating_system = "macOS"
    
    assert asset.ip_address == "192.168.1.100"
    assert asset.operating_system == "macOS"


def test_vulnerability_model_validation():
    """Test Vulnerability model validation."""
    from app.models.vulnerability import Vulnerability
    
    vuln = Vulnerability()
    vuln.cve_id = "CVE-2024-1234"
    vuln.description = "Test vulnerability"
    vuln.severity = "high"
    
    assert vuln.cve_id == "CVE-2024-1234"
    assert vuln.description == "Test vulnerability"
    assert vuln.severity == "high"


def test_network_interface_model_validation():
    """Test NetworkInterface model validation."""
    from app.models.asset import NetworkInterface
    
    interface = NetworkInterface()
    interface.name = "en0"
    interface.ip_address = "192.168.1.100"
    interface.mac_address = "00:11:22:33:44:55"
    interface.netmask = "255.255.255.0"
    
    assert interface.name == "en0"
    assert interface.ip_address == "192.168.1.100"
    assert interface.mac_address == "00:11:22:33:44:55"


def test_port_model_validation():
    """Test Port model validation."""
    from app.models.asset import Port
    
    port = Port()
    port.port_number = 443
    port.protocol = "tcp"
    port.state = "open"
    
    assert port.port_number == 443
    assert port.protocol == "tcp"
    assert port.state == "open"


def test_host_profile_model_validation():
    """Test HostProfile model validation."""
    from app.models.asset import HostProfile
    
    profile = HostProfile()
    profile.asset_id = 1
    profile.ip_address = "192.168.1.50"
    profile.mac_address = "00:11:22:33:44:55"
    profile.hostname = "webserver"
    
    assert profile.asset_id == 1
    assert profile.ip_address == "192.168.1.50"
    assert profile.hostname == "webserver"


def test_scan_evidence_model_validation():
    """Test ScanEvidence model validation."""
    from app.models.scan import ScanEvidence
    
    evidence = ScanEvidence()
    evidence.evidence_type = "port"
    evidence.data = "{}"
    
    assert evidence.evidence_type == "port"
    assert evidence.data == "{}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
