# NetScope Discovery Target Validation Tests

"""
Tests for target validation in discovery engines.
"""

import pytest
from app.core.validators import validate_cidr, validate_target_scope, AuthorizedScope


def test_discovery_target_validation_ipv4():
    """Test IPv4 target validation."""
    from app.core.validators import validate_ipv4
    
    # Valid IPv4 addresses
    assert validate_ipv4("192.168.1.1") is True
    assert validate_ipv4("10.0.0.1") is True
    assert validate_ipv4("172.16.0.1") is True
    
    # Invalid IPv4 addresses
    assert validate_ipv4("256.1.1.1") is False
    assert validate_ipv4("192.168.1") is False
    assert validate_ipv4("abc.def.ghi.jkl") is False


def test_discovery_target_validation_ipv6():
    """Test IPv6 target validation."""
    from app.core.validators import validate_ipv6
    
    # Valid IPv6 addresses
    assert validate_ipv6("::1") is True
    assert validate_ipv6("2001:db8::1") is True
    assert validate_ipv6("fe80::1") is True
    
    # Invalid IPv6 addresses
    assert validate_ipv6("gggg::1") is False


def test_discovery_target_validation_cidr():
    """Test CIDR target validation."""
    from app.core.validators import validate_cidr
    
    # Valid CIDRs
    assert validate_cidr("192.168.1.0/24") is True
    assert validate_cidr("10.0.0.0/8") is True
    assert validate_cidr("172.16.0.0/12") is True
    assert validate_cidr("::/0") is True
    
    # Invalid CIDRs
    assert validate_cidr("192.168.1.0/33") is False
    assert validate_cidr("abc.def.ghi.jkl/24") is False


def test_discovery_target_authorized_scope_private():
    """Test private IP address authorization."""
    from app.core.validators import validate_target_scope, AuthorizedScope
    
    # Private ranges should be authorized
    assert validate_target_scope("10.0.0.0/8", [AuthorizedScope.PRIVATE])[0] is True
    assert validate_target_scope("172.16.0.0/12", [AuthorizedScope.PRIVATE])[0] is True
    assert validate_target_scope("192.168.1.0/24", [AuthorizedScope.PRIVATE])[0] is True
    
    # Public IPs should not be authorized
    assert validate_target_scope("8.8.8.0/24", [AuthorizedScope.PRIVATE])[0] is False


def test_discovery_target_authorized_scope_loopback():
    """Test loopback IP authorization."""
    from app.core.validators import validate_target_scope, AuthorizedScope
    
    # Loopback should be authorized
    assert validate_target_scope("127.0.0.1", [AuthorizedScope.LOOPBACK])[0] is True
    assert validate_target_scope("::1", [AuthorizedScope.LOOPBACK])[0] is True


def test_discovery_target_authorized_scope_link_local():
    """Test link-local IP authorization."""
    from app.core.validators import validate_target_scope, AuthorizedScope
    
    # Link-local should be authorized
    assert validate_target_scope("169.254.0.1", [AuthorizedScope.LINK_LOCAL])[0] is True


def test_discovery_target_multiple_scopes():
    """Test target authorization with multiple scopes."""
    from app.core.validators import validate_target_scope, AuthorizedScope
    
    # Test multiple authorized scopes
    assert validate_target_scope("192.168.1.0/24", [AuthorizedScope.PRIVATE, AuthorizedScope.LOOPBACK])[0] is True
    assert validate_target_scope("127.0.0.1", [AuthorizedScope.PRIVATE, AuthorizedScope.LOOPBACK])[0] is True


def test_discovery_target_invalid_range():
    """Test rejection of invalid target ranges."""
    from app.core.validators import validate_cidr
    
    # Invalid CIDR ranges
    assert validate_cidr("192.168.1.0/33") is False
    assert validate_cidr("192.168.1.0/-1") is False
    assert validate_cidr("256.0.0.0/8") is False


def test_discovery_port_range_validation():
    """Test port range validation for scanning."""
    from app.core.validators import validate_port_range, common_ports
    
    # Valid port ranges
    assert validate_port_range(1, 1024)[0] is True
    assert validate_port_range(80, 443)[0] is True
    assert validate_port_range(1, 65535)[0] is True
    
    # Invalid port ranges
    assert validate_port_range(1, 70000)[0] is False
    assert validate_port_range(-1, 100)[0] is False
    assert validate_port_range(80, 40)[0] is False
    
    # Common ports
    common = common_ports()
    assert "minimal" in common
    assert "standard" in common
    assert "all_tcp" in common


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
