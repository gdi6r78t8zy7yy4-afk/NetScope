# NetScope Core Validators

"""
IP address and network validation utilities.
"""

import ipaddress
from typing import Union, Optional, Tuple, List
from enum import Enum


class NetworkType(Enum):
    """Types of network addresses."""
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    HOSTNAME = "hostname"


class AuthorizedScope(Enum):
    """Authorized network scopes."""
    PRIVATE = "private"  # RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
    LOOPBACK = "loopback"  # 127.0.0.0/8, ::1
    LINK_LOCAL = "link_local"  # 169.254.0.0/16, fe80::/10
    UNICAST = "unicast"  # All unicast addresses


def validate_ipv4(address: str) -> bool:
    """
    Validate IPv4 address format.
    
    Args:
        address: IPv4 address string (e.g., "192.168.1.1")
        
    Returns:
        bool: True if valid IPv4 format
    """
    try:
        ipaddress.IPv4Address(address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_ipv6(address: str) -> bool:
    """
    Validate IPv6 address format.
    
    Args:
        address: IPv6 address string (e.g., "2001:db8::1")
        
    Returns:
        bool: True if valid IPv6 format
    """
    try:
        ipaddress.IPv6Address(address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_cidr(cidr: str) -> bool:
    """
    Validate CIDR notation.
    
    Args:
        cidr: CIDR string (e.g., "192.168.1.0/24" or "2001:db8::/32")
        
    Returns:
        bool: True if valid CIDR format
    """
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except (ValueError, TypeError):
        return False


def get_network_type(target: str) -> Optional[NetworkType]:
    """
    Determine the type of network target.
    
    Args:
        target: IP address, hostname, or CIDR
        
    Returns:
        NetworkType or None if invalid
    """
    # Check for IPv4
    if validate_ipv4(target):
        return NetworkType.IPV4
    
    # Check for IPv6
    if validate_ipv6(target):
        return NetworkType.IPV6
    
    # Check for CIDR notation
    if "/" in target:
        if validate_cidr(target):
            net = ipaddress.ip_network(target, strict=False)
            return NetworkType.IPV4 if isinstance(net, ipaddress.IPv4Network) else NetworkType.IPV6
        return None
    
    # Check for hostname (simplified)
    if target and all(c.isalnum() or c in "-." for c in target):
        return NetworkType.HOSTNAME
    
    return None


def validate_target_scope(
    cidr: str,
    allowed_scopes: list[AuthorizedScope] = None
) -> Tuple[bool, str]:
    """
    Validate if a target is within authorized scopes.
    
    Args:
        cidr: CIDR to validate
        allowed_scopes: List of allowed scopes (default: private only)
        
    Returns:
        tuple: (is_authorized, message)
    """
    if allowed_scopes is None:
        allowed_scopes = [AuthorizedScope.PRIVATE]
    
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        return False, f"Invalid CIDR: {e}"
    
    # Determine the network type
    net_type = NetworkType.IPV4 if isinstance(net, ipaddress.IPv4Network) else NetworkType.IPV6
    
    # Check each scope
    for scope in allowed_scopes:
        if scope == AuthorizedScope.PRIVATE:
            # RFC 1918 private ranges
            if net_type == NetworkType.IPV4:
                private_ranges = [
                    ipaddress.ip_network("10.0.0.0/8"),
                    ipaddress.ip_network("172.16.0.0/12"),
                    ipaddress.ip_network("192.168.0.0/16"),
                ]
                for private_net in private_ranges:
                    if net.subnet_of(private_net) or net == private_net:
                        return True, "Target is within authorized private range"
            else:
                # IPv6 unique local addresses (fc00::/7)
                ula = ipaddress.ip_network("fc00::/7")
                if net.subnet_of(ula) or net == ula:
                    return True, "Target is within authorized ULA range"
                    
        elif scope == AuthorizedScope.LOOPBACK:
            loopback = ipaddress.ip_network("127.0.0.0/8") if net_type == NetworkType.IPV4 else ipaddress.ip_network("::1")
            if net.subnet_of(loopback) or net == loopback:
                return True, "Target is within authorized loopback range"
                
        elif scope == AuthorizedScope.LINK_LOCAL:
            link_local = ipaddress.ip_network("169.254.0.0/16") if net_type == NetworkType.IPV4 else ipaddress.ip_network("fe80::/10")
            if net.subnet_of(link_local) or net == link_local:
                return True, "Target is within authorized link-local range"
                
        elif scope == AuthorizedScope.UNICAST:
            # Allow all unicast addresses
            if net.is_global:
                return True, "Target is a valid unicast address"
    
    # Check if it's public but not in allowed scopes
    if net_type == NetworkType.IPV4:
        try:
            ipaddress.ip_address(str(net.network_address))
            return False, "Target is a public IP address not in authorized scopes"
        except ValueError:
            pass
    else:
        # IPv6 public address check
        if not net.is_private and not net.is_link_local and not net.is_loopback:
            return False, "Target is a public IPv6 address not in authorized scopes"
    
    return False, "Target does not match any authorized scope"


def validate_port_range(port_start: int, port_end: int) -> Tuple[bool, str]:
    """
    Validate port range configuration.
    
    Args:
        port_start: Start port number
        port_end: End port number
        
    Returns:
        tuple: (is_valid, message)
    """
    if not isinstance(port_start, int) or not isinstance(port_end, int):
        return False, "Port numbers must be integers"
    
    if port_start < 1 or port_start > 65535:
        return False, f"Start port {port_start} out of range (1-65535)"
    
    if port_end < 1 or port_end > 65535:
        return False, f"End port {port_end} out of range (1-65535)"
    
    if port_start > port_end:
        return False, f"Start port ({port_start}) cannot be greater than end port ({port_end})"
    
    return True, "Port range is valid"


def validate_port_list(ports: List[int]) -> Tuple[bool, str]:
    """
    Validate list of ports.
    
    Args:
        ports: List of port numbers
        
    Returns:
        tuple: (is_valid, message)
    """
    if not isinstance(ports, list):
        return False, "Ports must be a list"
    
    for port in ports:
        if not isinstance(port, int):
            return False, f"Port {port} is not an integer"
        if port < 1 or port > 65535:
            return False, f"Port {port} out of range (1-65535)"
    
    return True, "Port list is valid"


def parse_and_validate_ports(ports_string: str) -> Tuple[bool, Union[str, List[int]], str]:
    """
    Parse and validate ports string for SQL injection prevention.
    
    This function safely parses port specifications from user input
    and prevents SQL injection through port parsing.
    
    Args:
        ports_string: User-provided ports string (e.g., "22,80,443" or "1-1024")
        
    Returns:
        tuple: (is_valid, ports_or_error_message)
    """
    if not ports_string or not isinstance(ports_string, str):
        return False, [], "Ports must be a non-empty string"
    
    ports_string = ports_string.strip()
    
    if not ports_string:
        return False, [], "Ports must be a non-empty string"
    
    # Check for SQL injection patterns
    sql_injection_patterns = [
        "'", '"', ";", "--", "/*", "*/", "xp_", "sp_", "union", 
        "select", "insert", "update", "delete", "drop", "exec",
        "execute", "alter", "create", "truncate"
    ]
    
    ports_lower = ports_string.lower()
    for pattern in sql_injection_patterns:
        if pattern in ports_lower:
            return False, [], f"Invalid characters detected: potential SQL injection attempt"
    
    # Parse single port
    if ports_string.isdigit():
        port = int(ports_string)
        if 1 <= port <= 65535:
            return True, [port], f"Port {port} is valid"
        else:
            return False, [], f"Port {port} out of range (1-65535)"
    
    # Parse port list (comma-separated)
    if "," in ports_string:
        parts = ports_string.split(",")
        ports = []
        for part in parts:
            part = part.strip()
            if not part.isdigit():
                return False, [], f"Invalid port in list: {part}"
            port = int(part)
            if 1 <= port <= 65535:
                ports.append(port)
            else:
                return False, [], f"Port {port} out of range (1-65535)"
        
        if len(ports) == 0:
            return False, [], "Port list cannot be empty"
        
        if len(ports) > 1000:
            return False, [], "Port list too long (maximum 1000 ports)"
        
        return True, ports, f"Parsed {len(ports)} ports successfully"
    
    # Parse port range (e.g., "1-1024")
    if "-" in ports_string:
        parts = ports_string.split("-")
        if len(parts) != 2:
            return False, [], f"Invalid port range format: {ports_string}"
        
        start_str, end_str = parts[0].strip(), parts[1].strip()
        
        if not start_str.isdigit() or not end_str.isdigit():
            return False, [], f"Invalid port range values: {ports_string}"
        
        start = int(start_str)
        end = int(end_str)
        
        if not (1 <= start <= 65535) or not (1 <= end <= 65535):
            return False, [], f"Port range out of bounds (1-65535): {ports_string}"
        
        if start > end:
            return False, [], f"Start port ({start}) cannot be greater than end port ({end})"
        
        # Limit range size to prevent DoS
        if (end - start + 1) > 65535:
            return False, [], "Port range too large"
        
        return True, list(range(start, end + 1)), f"Parsed port range {start}-{end} successfully"
    
    return False, [], f"Invalid ports format: {ports_string}"


def common_ports() -> dict[str, List[int]]:
    """
    Return common port definitions.
    
    Returns:
        dict: Port preset names to port lists
    """
    return {
        "minimal": [21, 22, 23, 25],
        "basic": [21, 22, 23, 25, 53, 80, 110],
        "standard": [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445],
        "web": [80, 443, 8080, 8443],
        "mail": [25, 110, 143, 465, 993, 995],
        "database": [1433, 1521, 3306, 5432, 27017],
        "all_tcp": list(range(1, 65536)),
        "well_known": list(range(1, 1024)),
    }


# IP address validation
assert validate_ipv4("192.168.1.1") is True
assert validate_ipv4("256.1.1.1") is False
assert validate_ipv6("2001:db8::1") is True
assert validate_ipv6("gggg::1") is False

# CIDR validation
assert validate_cidr("192.168.1.0/24") is True
assert validate_cidr("192.168.1.0/33") is False
assert validate_cidr("2001:db8::/32") is True

# Scope validation
assert validate_target_scope("192.168.1.0/24", [AuthorizedScope.PRIVATE])[0] is True
assert validate_target_scope("10.0.0.0/8", [AuthorizedScope.PRIVATE])[0] is True
assert validate_target_scope("8.8.8.0/24", [AuthorizedScope.PRIVATE])[0] is False

# Port validation
assert validate_port_range(1, 1024)[0] is True
assert validate_port_range(1, 70000)[0] is False
assert validate_port_range(80, 443)[0] is True

# Port list validation
assert validate_port_list([22, 80, 443])[0] is True
assert validate_port_list([22, 80, 70000])[0] is False

if __name__ == "__main__":
    import sys
    
    print("Running IP/CIDR validation tests...")
    
    # Run assertions
    try:
        validate_ipv4("192.168.1.1")
        validate_cidr("10.0.0.0/8")
        validate_target_scope("172.16.0.0/12", [AuthorizedScope.PRIVATE])
        validate_port_range(1, 65535)
        
        print("All validation tests passed!")
    except AssertionError as e:
        print(f"Validation test failed: {e}")
        sys.exit(1)


# CVE ID validation
CVE_ID_PATTERN = r"^CVE-\d{4}-\d{4,}$"


def validate_cve_id(cve_id: str) -> Tuple[bool, str]:
    """
    Validate CVE ID format.
    
    Args:
        cve_id: CVE identifier string (e.g., "CVE-2024-1234")
        
    Returns:
        tuple: (is_valid, error_message)
    """
    import re
    
    if not cve_id or not isinstance(cve_id, str):
        return False, "CVE ID must be a non-empty string"
    
    cve_id = cve_id.strip()
    
    # Validate CVE ID format
    if not re.match(CVE_ID_PATTERN, cve_id):
        return False, f"Invalid CVE ID format: {cve_id}. Expected format: CVE-YYYY-N where YYYY is year and N is 4+ digits"
    
    return True, "Valid CVE ID format"


def sanitize_cve_id(cve_id: str) -> str:
    """
    Sanitize CVE ID for database queries.
    
    Args:
        cve_id: CVE identifier string
        
    Returns:
        str: Sanitized CVE ID
        
    Raises:
        ValueError: If CVE ID format is invalid
    """
    valid, message = validate_cve_id(cve_id)
    if not valid:
        raise ValueError(message)
    return cve_id.strip()
