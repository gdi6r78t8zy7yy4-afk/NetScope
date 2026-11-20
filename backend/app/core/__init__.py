# NetScope Core Module

"""
Core functionality and utilities for the NetScope backend.
"""

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.validators import (
    validate_scan_target,
    validate_scan_scope,
    validate_ipv4,
    validate_ipv6,
    validate_cidr,
    validate_hostname,
    validate_target_scope,
    AuthorizedScope,
    parse_and_validate_ports
)

__all__ = [
    "settings", 
    "hash_password", 
    "verify_password",
    "validate_scan_target",
    "validate_scan_scope",
    "validate_ipv4",
    "validate_ipv6",
    "validate_cidr",
    "validate_hostname",
    "validate_target_scope",
    "AuthorizedScope",
    "parse_and_validate_ports",
    "common_ports",
    "validate_port_range",
    "get_network_type",
    "NetworkType",
    "validate_port_list"
]
