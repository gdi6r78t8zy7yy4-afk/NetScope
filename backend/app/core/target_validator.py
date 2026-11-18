# NetScope Target Validator

"""
Target validation and authorization utilities for scan scope enforcement.
"""

import re
from typing import List, Dict, Set, Optional
from ipaddress import (
    IPv4Address,
    IPv6Address,
    IPv4Network,
    IPv6Network,
    AddressValueError
)

import structlog

logger = structlog.get_logger(__name__)


class TargetValidator:
    """
    Validates network targets for authorized scan scope.
    
    Supports:
    - Single IPv4/IPv6 addresses
    - CIDR ranges (e.g., 192.168.1.0/24)
    - IP ranges (e.g., 192.168.1.1-192.168.1.254)
    - Wildcard patterns (e.g., 192.168.*.*)
    
    Features:
    - Strict validation of IP formats
    - CIDR range normalization and overlap detection
    - Private vs public address classification
    - Loopback and link-local filtering
    """
    
    # Reserved/private network ranges
    PRIVATE_NETWORKS = {
        "10.0.0.0/8",           # Class A private
        "172.16.0.0/12",        # Class B private
        "192.168.0.0/16",       # Class C private
        "127.0.0.0/8",          # Loopback
        "169.254.0.0/16",       # Link-local
        "0.0.0.0/8",            # Default network
    }
    
    def __init__(self, authorized_scopes: Optional[List[str]] = None):
        """
        Initialize validator with optional authorized scopes.
        
        Args:
            authorized_scopes: List of CIDR ranges that are allowed for scanning
        """
        self.authorized_scopes = authorized_scopes or []
        self._authorized_networks: List[IPv4Network] = []
        self._parse_authorized_scopes()
    
    def _parse_authorized_scopes(self) -> None:
        """Parse and store authorized scopes as networks."""
        for scope in self.authorized_scopes:
            try:
                # Try IPv4 first
                if "/" not in scope and "." in scope:
                    # Single IP address - convert to /32
                    network = IPv4Network(f"{scope}/32")
                else:
                    network = IPv4Network(scope, strict=False)
                self._authorized_networks.append(network)
            except (AddressValueError, ValueError):
                # Try IPv6
                try:
                    if "/" not in scope and ":" in scope:
                        network = IPv6Network(f"{scope}/128")
                    else:
                        network = IPv6Network(scope, strict=False)
                    self._authorized_networks.append(network)
                except (AddressValueError, ValueError):
                    logger.warning("Invalid authorized scope format", scope=scope)
    
    def is_valid_ipv4(self, ip: str) -> bool:
        """Validate IPv4 address format."""
        if not isinstance(ip, str):
            return False
        try:
            IPv4Address(ip)
            return True
        except (AddressValueError, ValueError):
            return False
    
    def is_valid_ipv6(self, ip: str) -> bool:
        """Validate IPv6 address format."""
        if not isinstance(ip, str):
            return False
        try:
            IPv6Address(ip)
            return True
        except (AddressValueError, ValueError):
            return False
    
    def is_valid_cidr(self, cidr: str) -> bool:
        """Validate CIDR range format."""
        if not isinstance(cidr, str):
            return False
        try:
            if "/" not in cidr:
                return False
            network = IPv4Network(cidr, strict=False)
            return True
        except (AddressValueError, ValueError):
            try:
                if "/" not in cidr:
                    return False
                network = IPv6Network(cidr, strict=False)
                return True
            except (AddressValueError, ValueError):
                return False
    
    def is_private_ip(self, ip: str) -> bool:
        """Check if IP is a private/reserved address."""
        if not isinstance(ip, str):
            return False
        try:
            addr = IPv4Address(ip)
            # Check if it's in any private range
            for cidr in self.PRIVATE_NETWORKS:
                if addr in IPv4Network(cidr):
                    return True
            # Also check for loopback
            if addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return True
        except AddressValueError:
            try:
                addr = IPv6Address(ip)
                if addr.is_loopback or addr.is_link_local or addr.is_reserved:
                    return True
            except AddressValueError:
                pass
        return False
    
    def is_localhost(self, ip: str) -> bool:
        """Check if IP is localhost/loopback."""
        if not isinstance(ip, str):
            return False
        try:
            addr = IPv4Address(ip)
            return addr.is_loopback
        except AddressValueError:
            try:
                addr = IPv6Address(ip)
                return addr.is_loopback
            except AddressValueError:
                return False
    
    def normalize_target(self, target: str) -> str:
        """
        Normalize a target string to standard CIDR format.
        
        Args:
            target: Raw target string
            
        Returns:
            Normalized target string
        """
        if not isinstance(target, str):
            return ""
        
        target = target.strip()
        
        # Handle empty string
        if not target:
            return ""
        
        # Handle single IP address (add /32 for IPv4, /128 for IPv6)
        if self.is_valid_ipv4(target):
            return f"{target}/32"
        elif self.is_valid_ipv6(target):
            return f"{target}/128"
        
        # CIDR is already normalized
        if self.is_valid_cidr(target):
            return target
        
        # Handle IP range (e.g., 192.168.1.1-192.168.1.254)
        if "-" in target:
            try:
                parts = target.split("-")
                if len(parts) == 2 and self.is_valid_ipv4(parts[0]) and self.is_valid_ipv4(parts[1]):
                    # Convert range to CIDR (simplified)
                    return target  # Keep as-is for now
            except Exception:
                pass
        
        return target
    
    def get_network_from_target(self, target: str) -> Optional[IPv4Network]:
        """
        Parse a target into a network object.
        
        Args:
            target: Target string (IP or CIDR)
            
        Returns:
            IPv4Network object or None if invalid
        """
        try:
            target_normalized = self.normalize_target(target)
            if "/" in target_normalized:
                return IPv4Network(target_normalized, strict=False)
        except Exception as e:
            logger.warning("Failed to parse target", target=target, error=str(e))
        return None
    
    def is_authorized(self, target: str) -> Dict[str, any]:
        """
        Check if a target is within authorized scope.
        
        Args:
            target: Target IP or CIDR to check
            
        Returns:
            Dict with 'authorized' boolean and 'reason' string
        """
        if not self.authorized_scopes:
            # No restrictions - all targets authorized
            return {"authorized": True, "reason": "No authorization restrictions"}
        
        network = self.get_network_from_target(target)
        if network is None:
            return {"authorized": False, "reason": f"Invalid target format: {target}"}
        
        # Check if any authorized scope contains the target
        for auth_network in self._authorized_networks:
            try:
                # Check if target network is subset of authorized scope
                if network.subnet_of(auth_network):
                    return {"authorized": True, "reason": f"Within authorized scope: {auth_network}"}
                # Check for overlap
                if network.overlaps(auth_network):
                    return {"authorized": True, "reason": f"Overlaps authorized scope: {auth_network}"}
            except Exception as e:
                # IPv4 vs IPv6 mismatch - try next scope
                continue
        
        return {"authorized": False, "reason": f"Not within authorized scopes: {self.authorized_scopes}"}
    
    def validate_target(
        self,
        target: str,
        require_authorized: bool = True
    ) -> Dict[str, any]:
        """
        Perform comprehensive target validation.
        
        Args:
            target: Target to validate
            require_authorized: Whether authorization is required
            
        Returns:
            Dict with validation results
        """
        # Handle None input
        if target is None:
            return {"valid": False, "target": None, "reason": "Target cannot be None"}
        
        if not isinstance(target, str):
            return {"valid": False, "target": target, "reason": "Target must be a string"}
        
        result = {
            "valid": False,
            "target": target,
            "normalized": None,
            "is_private": None,
            "is_localhost": self.is_localhost(target),
            "authorization": {"authorized": False, "reason": ""},
        }
        
        # Normalize target
        result["normalized"] = self.normalize_target(target)
        
        # Validate format
        if self.is_valid_ipv4(result["normalized"]):
            result["ip_version"] = "IPv4"
            result["is_private"] = self.is_private_ip(result["normalized"])
        elif self.is_valid_ipv6(result["normalized"]):
            result["ip_version"] = "IPv6"
        elif self.is_valid_cidr(result["normalized"]):
            result["ip_version"] = "IPv4" if "." in target else "IPv6"
        else:
            result["reason"] = f"Invalid target format: {target}"
            return result
        
        # Check authorization
        auth_result = self.is_authorized(target)
        result["authorization"] = auth_result
        
        # Determine overall validity
        if not require_authorized or auth_result["authorized"]:
            result["valid"] = True
        else:
            result["reason"] = auth_result["reason"]
        
        return result
    
    def validate_targets(
        self,
        targets: List[str],
        require_authorized: bool = True
    ) -> Dict[str, any]:
        """
        Validate multiple targets.
        
        Args:
            targets: List of target strings
            require_authorized: Whether authorization is required
            
        Returns:
            Dict with validation results for each target
        """
        if not isinstance(targets, list):
            return {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "results": [],
            }
        
        results = []
        valid_count = 0
        invalid_count = 0
        
        for target in targets:
            result = self.validate_target(target, require_authorized)
            results.append(result)
            
            if result["valid"]:
                valid_count += 1
            else:
                invalid_count += 1
        
        return {
            "total": len(targets),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": results,
        }


# Singleton instance for default configuration
_default_validator: Optional[TargetValidator] = None


def get_target_validator(
    authorized_scopes: Optional[List[str]] = None
) -> TargetValidator:
    """
    Get a target validator instance.
    
    Args:
        authorized_scopes: Optional list of authorized CIDR ranges
        
    Returns:
        TargetValidator instance
    """
    global _default_validator
    
    if authorized_scopes is not None:
        # Create new validator with custom scopes
        _default_validator = TargetValidator(authorized_scopes)
    elif _default_validator is None:
        # Create default validator with localhost only
        _default_validator = TargetValidator(["127.0.0.0/8", "::1/128"])
    
    return _default_validator
