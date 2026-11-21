# NetScope IP/CIDR Validation Integration Tests

"""
Tests for IP address and CIDR validation.
"""

import pytest


def test_validate_ipv4_address():
    """Test IPv4 address validation."""
    from app.core.validators import validate_ipv4

    # Valid addresses
    assert validate_ipv4("0.0.0.0") is True
    assert validate_ipv4("255.255.255.255") is True
    assert validate_ipv4("192.168.1.1") is True
    assert validate_ipv4("10.0.0.1") is True
    assert validate_ipv4("172.16.0.1") is True

    # Invalid addresses
    assert validate_ipv4("256.0.0.1") is False
    assert validate_ipv4("192.168.1") is False
    assert validate_ipv4("192.168.1.256") is False
    assert validate_ipv4("abc.def.ghi.jkl") is False


def test_validate_ipv6_address():
    """Test IPv6 address validation."""
    from app.core.validators import validate_ipv6

    # Valid addresses
    assert validate_ipv6("::1") is True
    assert validate_ipv6("2001:db8::1") is True
    assert validate_ipv6("fe80::1") is True
    assert validate_ipv6("::") is True

    # Invalid addresses
    assert validate_ipv6("gggg::1") is False
    assert validate_ipv6(":::1") is False


def test_validate_cidr_notation():
    """Test CIDR notation validation."""
    from app.core.validators import validate_cidr

    # Valid CIDRs
    assert validate_cidr("192.168.1.0/24") is True
    assert validate_cidr("10.0.0.0/8") is True
    assert validate_cidr("172.16.0.0/12") is True
    assert validate_cidr("::/0") is True
    assert validate_cidr("2001:db8::/32") is True

    # Invalid CIDRs
    assert validate_cidr("192.168.1.0/33") is False
    assert validate_cidr("192.168.1.0/-1") is False
    assert validate_cidr("abc.def.ghi.jkl/24") is False


def test_get_network_type():
    """Test network type detection."""
    from app.core.validators import get_network_type, NetworkType

    assert get_network_type("192.168.1.1") == NetworkType.IPV4
    assert get_network_type("2001:db8::1") == NetworkType.IPV6
    assert get_network_type("192.168.1.0/24") == NetworkType.IPV4
    assert get_network_type("::1") == NetworkType.IPV6
    # Hostnames are detected as HOSTNAME type
    assert get_network_type("example.com") == NetworkType.HOSTNAME


def test_validate_target_scope_private():
    """Test private IP address validation."""
    from app.core.validators import validate_target_scope, AuthorizedScope

    # Private ranges should pass
    assert validate_target_scope("10.0.0.0/8",
                                 [AuthorizedScope.PRIVATE])[0] is True
    assert validate_target_scope("172.16.0.0/12",
                                 [AuthorizedScope.PRIVATE])[0] is True
    assert validate_target_scope("192.168.1.0/24",
                                 [AuthorizedScope.PRIVATE])[0] is True

    # Public IPs should fail
    assert validate_target_scope("8.8.8.0/24",
                                 [AuthorizedScope.PRIVATE])[0] is False
    assert validate_target_scope("1.1.1.0/24",
                                 [AuthorizedScope.PRIVATE])[0] is False


def test_validate_port_range():
    """Test port range validation."""
    from app.core.validators import validate_port_range

    # Valid ranges
    assert validate_port_range(1, 1024)[0] is True
    assert validate_port_range(80, 443)[0] is True
    assert validate_port_range(1, 65535)[0] is True

    # Invalid ranges
    assert validate_port_range(1, 70000)[0] is False
    assert validate_port_range(-1, 100)[0] is False
    assert validate_port_range(80, 40)[0] is False


def test_validate_port_list():
    """Test port list validation."""
    from app.core.validators import validate_port_list

    # Valid lists
    assert validate_port_list([22, 80, 443])[0] is True
    assert validate_port_list([1, 2, 3])[0] is True

    # Invalid lists
    assert validate_port_list([22, 80, 70000])[0] is False
    assert validate_port_list([])[0] is True  # Empty list is valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
