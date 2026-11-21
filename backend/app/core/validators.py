# NetScope Validators Module

"""
Target validation and scan safety utilities.
"""

import re
import ipaddress
from typing import List, Tuple, Set, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class TargetValidationResult:
    """Result of target validation."""

    valid: bool
    targets: List[str]
    errors: List[str]
    warnings: List[str]


def validate_ipv4(address: str) -> bool:
    """
    Validate IPv4 address.

    Args:
        address: IP address string to validate

    Returns:
        True if valid IPv4, False otherwise
    """
    try:
        ipaddress.IPv4Address(address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_ipv6(address: str) -> bool:
    """
    Validate IPv6 address.

    Args:
        address: IP address string to validate

    Returns:
        True if valid IPv6, False otherwise
    """
    try:
        ipaddress.IPv6Address(address)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def validate_cidr(cidr: str) -> bool:
    """
    Validate CIDR network notation.

    Args:
        cidr: CIDR string (e.g., "192.168.1.0/24")

    Returns:
        True if valid CIDR, False otherwise
    """
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except (ValueError, TypeError):
        return False


def validate_hostname(hostname: str) -> bool:
    """
    Validate hostname format.

    Args:
        hostname: Hostname string to validate

    Returns:
        True if valid hostname, False otherwise
    """
    if len(hostname) > 253:
        return False

    # RFC 1035 hostname rules
    if not re.match(r"^[a-zA-Z]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$", hostname):
        return False

    # Split by dots and validate each label
    labels = hostname.split(".")
    for label in labels:
        if len(label) == 0 or len(label) > 63:
            return False
        if not re.match(r"^[a-zA-Z]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$", label):
            return False

    return True


def parse_cidr_range(cidr: str) -> Tuple[str, int]:
    """
    Parse CIDR into network address and prefix length.

    Args:
        cidr: CIDR string

    Returns:
        Tuple of (network_address, prefix_length)
    """
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network.network_address), network.prefixlen


def get_cidr_size(cidr: str) -> int:
    """
    Get number of addresses in a CIDR range.

    Args:
        cidr: CIDR string

    Returns:
        Number of addresses
    """
    network = ipaddress.ip_network(cidr, strict=False)
    return network.num_addresses


def validate_scan_target(target: str) -> TargetValidationResult:
    """
    Validate a single scan target.

    Args:
        target: Single target (IP, CIDR, or hostname)

    Returns:
        Validation result with parsed targets and errors
    """
    errors = []
    warnings = []
    valid_targets = []

    target = target.strip()

    # Check for empty input
    if not target:
        errors.append("Empty target provided")
        return TargetValidationResult(
            valid=False, targets=[], errors=errors, warnings=warnings
        )

    # Try to parse as IPv4
    if validate_ipv4(target):
        valid_targets.append(target)
        return TargetValidationResult(
            valid=True, targets=valid_targets, errors=errors, warnings=warnings
        )

    # Try to parse as IPv6
    if validate_ipv6(target):
        valid_targets.append(target)
        return TargetValidationResult(
            valid=True, targets=valid_targets, errors=errors, warnings=warnings
        )

    # Try to parse as CIDR
    if "/" in target:
        if validate_cidr(target):
            # Check for large CIDR ranges
            num_addresses = get_cidr_size(target)
            if num_addresses > 65536:
                warnings.append(
                    f"Large network range: {num_addresses} addresses. "
                    "Consider using a smaller CIDR."
                )
            valid_targets.append(target)
            return TargetValidationResult(
                valid=True, targets=valid_targets, errors=errors, warnings=warnings
            )
        else:
            errors.append(f"Invalid CIDR notation: {target}")
            return TargetValidationResult(
                valid=False, targets=[], errors=errors, warnings=warnings
            )

    # Try to parse as hostname
    if validate_hostname(target):
        valid_targets.append(target)
        return TargetValidationResult(
            valid=True, targets=valid_targets, errors=errors, warnings=warnings
        )

    # If none of the above, it's invalid
    errors.append(
        f"Invalid target format: '{target}'. "
        "Expected IPv4, IPv6, CIDR network, or hostname."
    )

    return TargetValidationResult(
        valid=False, targets=[], errors=errors, warnings=warnings
    )


def validate_scan_scope(
    targets: List[str], authorized_networks: Optional[List[str]] = None
) -> TargetValidationResult:
    """
    Validate all scan targets and check against authorized networks.

    Args:
        targets: List of target strings
        authorized_networks: Optional list of authorized CIDR networks

    Returns:
        Validation result with all parsed targets
    """
    errors = []
    warnings = []
    valid_targets = []

    if not targets:
        errors.append("No targets provided for scan")
        return TargetValidationResult(
            valid=False, targets=[], errors=errors, warnings=warnings
        )

    # Validate each target individually
    for target in targets:
        result = validate_scan_target(target)

        if not result.valid:
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            continue

        # Check against authorized networks if specified
        if authorized_networks:
            target_is_authorized = False

            for auth_network in authorized_networks:
                try:
                    # Check if target is within authorized network
                    auth_net = ipaddress.ip_network(auth_network, strict=False)

                    # Handle single IPs and hostnames differently
                    if validate_ipv4(target) or validate_ipv6(target):
                        try:
                            target_ip = ipaddress.ip_address(target)
                            if target_ip in auth_net:
                                target_is_authorized = True
                                break
                        except ValueError:
                            pass

                    # Handle CIDR ranges
                    elif "/" in target and validate_cidr(target):
                        try:
                            target_net = ipaddress.ip_network(
                                target, strict=False)
                            # Check if target network is subset of authorized
                            if target_net.subnet_of(auth_net):
                                target_is_authorized = True
                                break
                        except ValueError:
                            pass

                    # Handle hostnames - check if they resolve within
                    # authorized networks
                    elif validate_hostname(target):
                        warnings.append(
                            f"Hostname '{target}' cannot be validated against "
                            "authorized networks without DNS resolution"
                        )
                        target_is_authorized = True
                        break

                except ValueError:
                    continue

            if not target_is_authorized:
                errors.append(
                    f"Target '{target}' is not within authorized networks")
                continue

        valid_targets.extend(result.targets)

    # Check if we have any valid targets
    if not valid_targets and errors:
        return TargetValidationResult(
            valid=False, targets=[], errors=errors, warnings=warnings
        )

    # Check total scope size
    total_addresses = 0
    for target in valid_targets:
        if "/" in target and validate_cidr(target):
            total_addresses += get_cidr_size(target)
        elif validate_ipv4(target) or validate_ipv6(target):
            total_addresses += 1

    if total_addresses > 256 * 256:  # /8 network equivalent
        warnings.append(
            f"Large scan scope: {total_addresses} addresses. "
            "This may take a long time and impact system resources."
        )

    return TargetValidationResult(
        valid=True, targets=valid_targets, errors=errors, warnings=warnings
    )


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        value: User input string

    Returns:
        Sanitized string
    """
    # Remove null bytes
    value = value.replace("\x00", "")

    # Remove control characters (except newlines and tabs)
    value = "".join(c for c in value if c.isprintable() or c in "\n\t")

    # Trim whitespace
    value = value.strip()

    return value


def is_safe_target(target: str) -> bool:
    """
    Check if target is safe to scan (not a local system or reserved range).

    Args:
        target: IP address or CIDR to check

    Returns:
        True if safe, False otherwise
    """
    try:
        # Check if it's a valid IP or CIDR
        if validate_ipv4(target):
            ip = ipaddress.IPv4Address(target)
        elif validate_ipv6(target):
            ip = ipaddress.IPv6Address(target)
        elif validate_cidr(target):
            network = ipaddress.ip_network(target, strict=False)

            # Check each address in the range
            for addr in network:
                if is_safe_address(addr):
                    continue
                return False

            return True
        else:
            # Hostname - assume safe for now (DNS validation happens later)
            return True

        return is_safe_address(ip)

    except (ValueError, TypeError):
        return False


def is_safe_address(address) -> bool:
    """
    Check if a single IP address is safe to scan.

    Args:
        address: IP address object

    Returns:
        True if safe, False otherwise
    """
    # Localhost
    if address.is_loopback:
        return False

    # Link-local addresses
    if isinstance(address, ipaddress.IPv4Address):
        if address.is_link_local or address.is_private or address.is_reserved:
            return False
    else:
        if address.is_link_local or address.is_private or address.is_reserved:
            return False

    # Private network ranges (should not scan without explicit authorization)
    private_ranges = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    for private_range in private_ranges:
        if address in private_range:
            return False

    return True


def parse_target_list(target_string: str, delimiter: str = ",") -> List[str]:
    """
    Parse a comma-separated list of targets.

    Args:
        target_string: Comma-separated string of targets
        delimiter: Delimiter character (default: comma)

    Returns:
        List of target strings
    """
    if not target_string:
        return []

    # Split by delimiter and clean up whitespace
    targets = [t.strip() for t in target_string.split(delimiter)]

    # Remove empty strings
    targets = [t for t in targets if t]

    return targets


def parse_and_validate_ports(ports_string: str) -> Tuple[bool, List[int], str]:
    """
    Parse and validate a ports string.

    Args:
        ports_string: String containing port specification

    Returns:
        Tuple of (is_valid, parsed_ports, message)
    """
    if not ports_string or not ports_string.strip():
        return False, [], "No ports specified"

    ports_string = sanitize_input(ports_string)

    # Allowed characters: digits, commas, dashes
    import re

    if not re.match(r"^[\d,\-\s]+$", ports_string):
        return False, [], "Invalid characters in port specification"

    try:
        parsed_ports = []

        # Handle comma-separated list
        for part in ports_string.split(","):
            part = part.strip()

            if not part:
                continue

            # Handle port ranges
            if "-" in part:
                range_parts = part.split("-")

                if len(range_parts) != 2:
                    return False, [], f"Invalid port range: {part}"

                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())

                if start > end:
                    return False, [
                    ], f"Invalid port range (start > end): {part}"

                if start < 1 or end > 65535:
                    return False, [], f"Port out of range (1-65535): {part}"

                # Validate range size
                if end - start + 1 > 1000:
                    return False, [
                    ], f"Port range too large (>1000 ports): {part}"

                parsed_ports.extend(range(start, end + 1))
            else:
                # Single port
                port = int(part)

                if port < 1 or port > 65535:
                    return False, [], f"Port out of range (1-65535): {port}"

                parsed_ports.append(port)

        # Limit total ports
        if len(parsed_ports) > 10000:
            return False, [], f"Too many ports (>10000): {len(parsed_ports)}"

        return True, parsed_ports, f"Successfully parsed {len(parsed_ports)} port(s)"

    except ValueError as e:
        return False, [], f"Invalid port value: {e}"


class AuthorizedScope:
    """
    Represents an authorized network scope for scanning.

    Attributes:
        name: Human-readable name of the scope
        cidr: Network CIDR that defines the scope
        description: Optional description of what this scope covers
    """

    # Predefined authorized scopes (class attributes)
    PRIVATE = None  # Will be set after class definition
    LOOPBACK = None  # Will be set after class definition
    LINK_LOCAL = None  # Will be set after class definition

    def __init__(self, name: str, cidr: str,
                 description: Optional[str] = None):
        self.name = name
        self.cidr = cidr
        self.description = description

    def __repr__(self):
        return f"AuthorizedScope(name='{self.name}', cidr='{self.cidr}')"

    @classmethod
    def create(
        cls, name: str, cidr: str, description: Optional[str] = None
    ) -> "AuthorizedScope":
        """Create a new AuthorizedScope instance."""
        return cls(name, cidr, description)


# Define the class-level scopes after class definition
AuthorizedScope.PRIVATE = AuthorizedScope.create(
    name="Private Networks",
    cidr="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    description="Private network ranges",
)

AuthorizedScope.LOOPBACK = AuthorizedScope.create(
    name="Loopback", cidr="127.0.0.0/8,::1/128", description="Local loopback addresses"
)

AuthorizedScope.LINK_LOCAL = AuthorizedScope.create(
    name="Link-Local", cidr="169.254.0.0/16", description="Link-local addresses"
)


def common_ports() -> Dict[str, List[int]]:
    """
    Get commonly used ports for scanning.

    Returns:
        Dict of port preset names to lists of port numbers
    """
    return {
        "minimal": [22, 80, 443],  # SSH, HTTP, HTTPS
        "standard": [
            21,  # FTP
            22,  # SSH
            23,  # Telnet (deprecated)
            25,  # SMTP
            53,  # DNS
            80,  # HTTP
            110,  # POP3
            123,  # NTP
            143,  # IMAP
            443,  # HTTPS
            993,  # IMAPS
            995,  # POP3S
        ],
        "all_tcp": list(range(1, 1024)),  # Well-known TCP ports
        "all_udp": list(range(1, 1024)),  # Well-known UDP ports
    }


def validate_port_range(start: int, end: int) -> Tuple[bool, str]:
    """
    Validate a port range.

    Args:
        start: Start port number
        end: End port number

    Returns:
        Tuple of (is_valid, message)
    """
    if start < 1 or end > 65535:
        return False, "Port numbers must be between 1 and 65535"

    if start > end:
        return False, "Start port must be less than or equal to end port"

    # Allow full range scan
    return True, f"Valid port range: {start}-{end}"


def validate_target_scope(
    target: str, authorized_scopes: List[AuthorizedScope]
) -> Tuple[bool, Optional[AuthorizedScope], str]:
    """
    Validate if a target is within any authorized scope.

    Args:
        target: IP address or CIDR to validate
        authorized_scopes: List of authorized network scopes

    Returns:
        Tuple of (is_authorized, matching_scope, message)
    """
    if not authorized_scopes:
        return False, None, "No authorized scopes configured"

    try:
        # Parse target
        if validate_ipv4(target) or validate_ipv6(target):
            target_ip = ipaddress.ip_address(target)
        elif validate_cidr(target):
            target_net = ipaddress.ip_network(target, strict=False)
        else:
            return False, None, f"Invalid target format: {target}"

        # Check against authorized scopes
        for scope in authorized_scopes:
            # Split comma-separated CIDRs (for PRIVATE scope)
            cidrs = [c.strip() for c in scope.cidr.split(",")]

            for cidr_str in cidrs:
                try:
                    auth_net = ipaddress.ip_network(cidr_str, strict=False)

                    # Check if target is a single IP
                    if validate_ipv4(target) or validate_ipv6(target):
                        # Check if single IP is in network
                        if target_ip in auth_net:
                            return (
                                True,
                                scope,
                                f"Target within authorized scope: {scope.name}",
                            )
                    else:
                        # Check if target network is subset of authorized
                        if target_net.subnet_of(auth_net):
                            return (
                                True,
                                scope,
                                f"Target within authorized scope: {scope.name}",
                            )

                except ValueError:
                    continue

        return False, None, "Target not within any authorized scope"

    except (ValueError, TypeError) as e:
        return False, None, f"Error validating target: {e}"


@dataclass
class NetworkType:
    """Network type enumeration."""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    HOSTNAME = "hostname"


def get_network_type(target: str) -> NetworkType:
    """
    Detect the network type of a target.

    Args:
        target: IP address, CIDR, or hostname

    Returns:
        NetworkType enum value
    """
    # Check for CIDR notation first (has /)
    if "/" in target:
        # CIDR is always IPv4 (or we need separate CIDR type)
        return NetworkType.IPV4

    if validate_ipv4(target):
        return NetworkType.IPV4
    elif validate_ipv6(target):
        return NetworkType.IPV6
    else:
        # Assume hostname if not IP/CIDR
        return NetworkType.HOSTNAME


def validate_port_list(ports: List[int]) -> Tuple[bool, str]:
    """
    Validate a list of ports.

    Args:
        ports: List of port numbers

    Returns:
        Tuple of (is_valid, message)
    """
    if not ports:
        return True, "Empty port list is valid (no ports to validate)"

    for port in ports:
        if not isinstance(port, int) or port < 1 or port > 65535:
            return False, f"Invalid port number: {port}"

    return True, f"Valid port list with {len(ports)} ports"
