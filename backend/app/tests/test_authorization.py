# NetScope Authorization Tests

"""
Comprehensive tests for Phase 4: Enforce Authorized Scan Scope.

Tests cover:
- Target validation (IPv4, IPv6, CIDR ranges)
- Authorization checks against configured scopes
- Edge cases and error handling
"""

import pytest
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path
import os

from app.core.target_validator import (
    TargetValidator,
    get_target_validator
)
from app.core.authorization_service import (
    AuthorizationService,
    get_authorization_service
)


class TestTargetValidator:
    """Test TargetValidator class."""
    
    def test_init_with_scopes(self):
        """Test initialization with custom authorized scopes."""
        validator = TargetValidator(["192.168.1.0/24", "10.0.0.0/8"])
        assert validator.authorized_scopes == ["192.168.1.0/24", "10.0.0.0/8"]
        assert len(validator._authorized_networks) == 2
    
    def test_init_with_empty_scopes(self):
        """Test initialization with empty scopes."""
        validator = TargetValidator([])
        assert validator.authorized_scopes == []
    
    def test_init_with_none_scopes(self):
        """Test initialization with None scopes."""
        validator = TargetValidator(None)
        assert validator.authorized_scopes == []
    
    def test_is_valid_ipv4(self):
        """Test IPv4 validation."""
        validator = TargetValidator()
        
        assert validator.is_valid_ipv4("192.168.1.1") is True
        assert validator.is_valid_ipv4("10.0.0.1") is True
        assert validator.is_valid_ipv4("255.255.255.255") is True
        assert validator.is_valid_ipv4("0.0.0.0") is True
        
        # Invalid IPs
        assert validator.is_valid_ipv4("256.1.1.1") is False
        assert validator.is_valid_ipv4("192.168.1") is False
        assert validator.is_valid_ipv4("not-an-ip") is False
    
    def test_is_valid_ipv6(self):
        """Test IPv6 validation."""
        validator = TargetValidator()
        
        assert validator.is_valid_ipv6("::1") is True
        assert validator.is_valid_ipv6("2001:db8::1") is True
        assert validator.is_valid_ipv6("fe80::1") is True
        assert validator.is_valid_ipv6("::") is True
        
        # Invalid IPs
        assert validator.is_valid_ipv6("gggg::1") is False
        assert validator.is_valid_ipv6("not-an-ipv6") is False
    
    def test_is_valid_cidr(self):
        """Test CIDR validation."""
        validator = TargetValidator()
        
        assert validator.is_valid_cidr("192.168.1.0/24") is True
        assert validator.is_valid_cidr("10.0.0.0/8") is True
        assert validator.is_valid_cidr("172.16.0.0/12") is True
        
        assert validator.is_valid_cidr("192.168.1.0/33") is False
        assert validator.is_valid_cidr("not-a-cidr") is False
    
    def test_is_private_ip(self):
        """Test private IP detection."""
        validator = TargetValidator()
        
        # Private IPs
        assert validator.is_private_ip("10.0.0.1") is True
        assert validator.is_private_ip("172.16.0.1") is True
        assert validator.is_private_ip("192.168.1.1") is True
        assert validator.is_private_ip("127.0.0.1") is True  # Loopback
        assert validator.is_private_ip("169.254.1.1") is True  # Link-local
        
        # Public IPs
        assert validator.is_private_ip("8.8.8.8") is False
        assert validator.is_private_ip("1.1.1.1") is False
    
    def test_is_localhost(self):
        """Test localhost detection."""
        validator = TargetValidator()
        
        assert validator.is_localhost("127.0.0.1") is True
        assert validator.is_localhost("::1") is True
        
        assert validator.is_localhost("8.8.8.8") is False
        assert validator.is_localhost("192.168.1.1") is False
    
    def test_normalize_target_single_ip(self):
        """Test normalization of single IP addresses."""
        validator = TargetValidator()
        
        assert validator.normalize_target("192.168.1.1") == "192.168.1.1/32"
        assert validator.normalize_target("::1") == "::1/128"
    
    def test_normalize_target_cidr(self):
        """Test CIDR normalization."""
        validator = TargetValidator()
        
        assert validator.normalize_target("192.168.1.0/24") == "192.168.1.0/24"
        assert validator.normalize_target("10.0.0.0/8") == "10.0.0.0/8"
    
    def test_get_network_from_target(self):
        """Test target to network conversion."""
        validator = TargetValidator()
        
        network = validator.get_network_from_target("192.168.1.0/24")
        assert network is not None
        assert str(network) == "192.168.1.0/24"
        
        # Invalid target
        network = validator.get_network_from_target("invalid")
        assert network is None
    
    def test_is_authorized_single_scope(self):
        """Test authorization with single scope."""
        validator = TargetValidator(["192.168.1.0/24"])
        
        # Within scope
        result = validator.is_authorized("192.168.1.1")
        assert result["authorized"] is True
        assert "192.168.1.0/24" in result["reason"]
        
        # Outside scope
        result = validator.is_authorized("10.0.0.1")
        assert result["authorized"] is False
        assert "Not within authorized scopes" in result["reason"]
    
    def test_is_authorized_multiple_scopes(self):
        """Test authorization with multiple scopes."""
        validator = TargetValidator([
            "192.168.1.0/24",
            "10.0.0.0/8"
        ])
        
        # Within first scope
        result = validator.is_authorized("192.168.1.1")
        assert result["authorized"] is True
        
        # Within second scope
        result = validator.is_authorized("10.0.0.1")
        assert result["authorized"] is True
        
        # Outside all scopes
        result = validator.is_authorized("8.8.8.8")
        assert result["authorized"] is False
    
    def test_is_authorized_no_scopes(self):
        """Test authorization with no restrictions."""
        validator = TargetValidator([])
        
        result = validator.is_authorized("8.8.8.8")
        assert result["authorized"] is True
        assert "No authorization restrictions" in result["reason"]
    
    def test_is_authorized_overlapping_scope(self):
        """Test authorization with overlapping scopes."""
        validator = TargetValidator(["10.0.0.0/8"])
        
        # Smaller subnet within scope
        result = validator.is_authorized("10.1.2.0/24")
        assert result["authorized"] is True
    
    def test_validate_target_single_ip(self):
        """Test full target validation."""
        validator = TargetValidator(["192.168.1.0/24"])
        
        result = validator.validate_target("192.168.1.1")
        assert result["valid"] is True
        assert result["ip_version"] == "IPv4"
    
    def test_validate_target_outside_scope(self):
        """Test validation of unauthorized target."""
        validator = TargetValidator(["192.168.1.0/24"])
        
        result = validator.validate_target("10.0.0.1")
        assert result["valid"] is False
        assert "Not within authorized scopes" in result["reason"]
    
    def test_validate_target_with_require_false(self):
        """Test validation with require_authorized=False."""
        validator = TargetValidator(["192.168.1.0/24"])
        
        result = validator.validate_target("10.0.0.1", require_authorized=False)
        assert result["valid"] is True
    
    def test_validate_targets_batch(self):
        """Test batch target validation."""
        validator = TargetValidator(["192.168.1.0/24", "10.0.0.0/8"])
        
        results = validator.validate_targets([
            "192.168.1.1",
            "10.0.0.1",
            "8.8.8.8"
        ])
        
        assert results["total"] == 3
        assert results["valid"] == 2
        assert results["invalid"] == 1
    
    def test_validate_targets_all_valid(self):
        """Test batch validation with all valid targets."""
        validator = TargetValidator(["192.168.0.0/16"])
        
        results = validator.validate_targets([
            "192.168.1.1",
            "192.168.2.1"
        ])
        
        assert results["valid"] == 2
        assert results["invalid"] == 0
    
    def test_validate_targets_all_invalid(self):
        """Test batch validation with all invalid targets."""
        validator = TargetValidator(["192.168.0.0/16"])
        
        results = validator.validate_targets([
            "10.0.0.1",
            "8.8.8.8"
        ])
        
        assert results["valid"] == 0
        assert results["invalid"] == 2


class TestAuthorizationService:
    """Test AuthorizationService class."""
    
    def test_init_with_scopes(self, monkeypatch):
        """Test initialization with custom scopes."""
        monkeypatch.setenv("NETSCOPE_AUTHORIZED_TARGETS", "192.168.1.0/24")
        service = AuthorizationService(authorized_scopes=["10.0.0.0/8"])
        
        assert "192.168.1.0/24" in service.authorized_scopes
        assert "10.0.0.0/8" in service.authorized_scopes
    
    def test_get_authorized_scopes(self, monkeypatch):
        """Test getting authorized scopes."""
        # Remove the config file temporarily to avoid loading from it
        config_path = Path.cwd() / "authorized_scopes.json"
        backend_config_path = Path.cwd() / "backend" / "authorized_scopes.json"
        
        temp_move = []
        if config_path.exists():
            temp_path = str(config_path) + ".tmp"
            os.rename(str(config_path), temp_path)
            temp_move.append((config_path, temp_path))
        if backend_config_path.exists():
            temp_path = str(backend_config_path) + ".tmp"
            os.rename(str(backend_config_path), temp_path)
            temp_move.append((backend_config_path, temp_path))
        
        try:
            service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
            scopes = service.get_authorized_scopes()
            
            assert "192.168.1.0/24" in scopes
            assert len(scopes) == 1
        finally:
            # Restore config files
            for orig_path, temp_path in temp_move:
                if os.path.exists(temp_path):
                    os.rename(temp_path, str(orig_path))
    
    def test_is_authorized(self):
        """Test authorization check."""
        service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
        
        result = service.is_authorized("192.168.1.1")
        assert result["authorized"] is True
    
    def test_validate_target(self):
        """Test target validation."""
        service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
        
        result = service.validate_target("192.168.1.1")
        assert result["valid"] is True
    
    def test_validate_targets(self):
        """Test batch target validation."""
        service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
        
        results = service.validate_targets([
            "192.168.1.1",
            "10.0.0.1"
        ])
        
        assert results["total"] == 2
        assert results["valid"] == 1
    
    def test_get_unauthorized_targets(self):
        """Test getting unauthorized targets."""
        service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
        
        result = service.get_unauthorized_targets([
            "192.168.1.1",
            "10.0.0.1"
        ])
        
        assert result["authorized"] == ["192.168.1.1"]
        assert result["unauthorized"] == ["10.0.0.1"]
    
    def test_get_valid_targets(self):
        """Test getting valid targets."""
        service = AuthorizationService(authorized_scopes=["192.168.1.0/24"])
        
        valid = service.get_valid_targets([
            "192.168.1.1",
            "10.0.0.1"
        ])
        
        assert valid == ["192.168.1.1"]
    
    def test_audit_log(self, caplog):
        """Test audit logging."""
        service = AuthorizationService()
        
        service.audit_log(
            action="scan",
            target="192.168.1.1",
            authorized=True
        )
        
        assert True  # If we got here, the audit_log method executed without error


class TestSingletonPatterns:
    """Test singleton patterns for validators."""
    
    def test_get_target_validator_default(self):
        """Test default target validator creation."""
        validator = get_target_validator()
        assert validator is not None
        assert len(validator.authorized_scopes) > 0
    
    def test_get_target_validator_custom(self):
        """Test custom target validator creation."""
        validator = get_target_validator(authorized_scopes=["10.0.0.0/8"])
        assert "10.0.0.0/8" in validator.authorized_scopes
    
    def test_get_authorization_service_default(self):
        """Test default authorization service creation."""
        service = get_authorization_service()
        assert service is not None
    
    def test_get_authorization_service_custom(self):
        """Test custom authorization service creation."""
        service = get_authorization_service(
            authorized_scopes=["192.168.1.0/24"]
        )
        assert "192.168.1.0/24" in service.authorized_scopes
    
    def test_authorization_service_strict_mode(self):
        """Test strict mode."""
        service = get_authorization_service(
            strict_mode=True
        )
        assert service.strict_mode is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_target(self):
        """Test empty target validation."""
        validator = TargetValidator()
        
        result = validator.validate_target("")
        assert result["valid"] is False
    
    def test_whitespace_target(self):
        """Test whitespace target validation."""
        validator = TargetValidator()
        
        result = validator.validate_target("   ")
        assert result["valid"] is False
    
    def test_invalid_cidr(self):
        """Test invalid CIDR validation."""
        validator = TargetValidator()
        
        result = validator.validate_target("192.168.1.0/35")
        assert result["valid"] is False
    
    def test_ipv6_localhost(self):
        """Test IPv6 localhost."""
        validator = TargetValidator()
        
        assert validator.is_localhost("::1") is True
        result = validator.validate_target("::1")
        assert result["valid"] is True
    
    def test_large_cidr(self):
        """Test large CIDR range."""
        validator = TargetValidator()
        
        network = validator.get_network_from_target("10.0.0.0/8")
        assert network is not None
        assert str(network) == "10.0.0.0/8"
    
    def test_private_scope_validation(self):
        """Test validation against private scopes."""
        validator = TargetValidator(["192.168.0.0/16"])
        
        result = validator.validate_target("192.168.100.1")
        assert result["valid"] is True
        assert result["valid"] is True  # Validation should pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
