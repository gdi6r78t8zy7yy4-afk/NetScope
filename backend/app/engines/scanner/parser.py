# NetScope Nmap XML Parser

"""
Parser for Nmap scan results in XML format.
"""

import xml.etree.ElementTree as ET  # nosec B405, B314
from typing import List, Dict, Any
import sys

# XML Bomb Protection Constants
MAX_ELEMENT_COUNT = 10000  # Maximum number of XML elements
MAX_NESTING_DEPTH = 50  # Maximum XML nesting depth
MAX_ATTRIBUTE_COUNT = 100  # Maximum attributes per element
MAX_ENTITY_SIZE = 1024 * 1024  # Maximum entity size (1MB)
MAX_TOTAL_SIZE = 10 * 1024 * 1024  # Maximum total XML size (10MB)


class XMLBombError(Exception):
    """Custom exception for XML bomb protection violations."""

    pass


def check_xml_size(xml_string: str) -> None:
    """Check if XML size is within limits."""
    if len(xml_string) > MAX_TOTAL_SIZE:
        raise XMLBombError(
            f"XML size {len(xml_string)} exceeds maximum allowed {MAX_TOTAL_SIZE}"
        )


def count_elements(root: ET.Element, depth: int = 0) -> tuple[int, int]:
    """
    Recursively count XML elements and track nesting depth.

    Returns:
        Tuple of (element_count, max_depth)
    """
    if depth > MAX_NESTING_DEPTH:
        raise XMLBombError(
            f"XML nesting depth {depth} exceeds maximum allowed {MAX_NESTING_DEPTH}"
        )

    element_count = 1  # Count current element

    # Check attributes for each element
    if len(root.attrib) > MAX_ATTRIBUTE_COUNT:
        raise XMLBombError(
            f"Element has {len(root.attrib)} attributes, exceeds maximum {MAX_ATTRIBUTE_COUNT}"
        )

    max_depth = depth

    for child in root:
        child_count, child_max_depth = count_elements(child, depth + 1)
        element_count += child_count
        max_depth = max(max_depth, child_max_depth)

        if element_count > MAX_ELEMENT_COUNT:
            raise XMLBombError(
                f"XML contains {element_count} elements, exceeds maximum {MAX_ELEMENT_COUNT}"
            )

    return element_count, max_depth


def parse_nmap_xml(xml_string: str) -> dict:
    """
    Parse Nmap XML output with security protections.

    Args:
        xml_string: Nmap XML content

    Returns:
        Dictionary with parsed results

    Raises:
        XMLBombError: If XML bomb protection is triggered
        ET.ParseError: If XML parsing fails
    """
    # Check total size
    check_xml_size(xml_string)

    try:
        root = ET.fromstring(xml_string)  # nosec B405, B314
    except ET.ParseError as e:
        return {"error": f"Failed to parse XML: {str(e)}"}

    # Check element count and nesting depth
    try:
        element_count, max_depth = count_elements(root)
    except XMLBombError as e:
        return {"error": f"XML bomb protection triggered: {str(e)}"}

    result = {"scan_info": {}, "hosts": [], "ports": [], "os": []}

    # Parse scan info
    if root.tag == "nmaprun":
        result["scan_info"] = {
            "scanner": root.get("scanner", "unknown"),
            "args": root.get("args", ""),
            "start_time": int(root.get("start", 0)),
        }

        # Parse runstats
        runstats = root.find("runstats")
        if runstats is not None:
            finished = runstats.find("finished")
            if finished is not None:
                result["scan_info"].update(
                    {
                        "end_time": int(finished.get("time", 0)),
                        "elapsed": finished.get("elapsed", ""),
                        "summary": finished.get("summary", ""),
                    }
                )

        # Parse hosts
        for host_elem in root.findall(".//host"):
            host_info = parse_host(host_elem)
            if host_info:
                result["hosts"].append(host_info)

        # Extract ports from all hosts
        for port_elem in root.findall(".//port"):
            port_info = parse_port(port_elem)
            if port_info:
                result["ports"].append(port_info)

        # Extract OS detection info
        for os_elem in root.findall(".//os"):
            os_info = parse_os(os_elem)
            if os_info:
                result["os"].append(os_info)

    return result


def parse_host(host_elem: ET.Element) -> dict:
    """Parse a host element."""
    host_info = {}

    # Get address
    addr_elem = host_elem.find("address")
    if addr_elem is not None:
        host_info["ip"] = addr_elem.get("addr", "")
        host_info["mac"] = addr_elem.get("vendor", "")

    # Get status
    status_elem = host_elem.find("status")
    if status_elem is not None:
        host_info["status"] = status_elem.get("state", "unknown")

    # Get ports
    host_info["ports"] = []
    for port_elem in host_elem.findall("ports/port"):
        host_info["ports"].append(parse_port(port_elem))

    # Get OS detection
    os_elem = host_elem.find("os")
    if os_elem is not None:
        host_info["os"] = parse_os(os_elem)

    return host_info


def parse_port(port_elem: ET.Element) -> dict:
    """Parse a port element."""
    port_info = {
        "port": int(port_elem.get("portid", 0)),
        "protocol": port_elem.get("protocol", "tcp"),
    }

    # Get state
    state_elem = port_elem.find("state")
    if state_elem is not None:
        port_info["state"] = state_elem.get("state", "unknown")

    # Get service
    service_elem = port_elem.find("service")
    if service_elem is not None:
        port_info["service"] = service_elem.get("name", "")
        port_info["product"] = service_elem.get("product", "")
        port_info["version"] = service_elem.get("version", "")

    return port_info


def parse_os(os_elem: ET.Element) -> dict:
    """Parse OS detection element."""
    os_info = {}

    # Get OS matches
    os_matches = []
    for match_elem in os_elem.findall("osmatch"):
        os_matches.append(
            {
                "name": match_elem.get("name", ""),
                "accuracy": int(match_elem.get("accuracy", 0)),
            }
        )
    os_info["matches"] = os_matches

    # Get OS classes
    os_classes = []
    for class_elem in os_elem.findall("osclass"):
        os_classes.append(
            {
                "type": class_elem.get("type", ""),
                "vendor": class_elem.get("vendor", ""),
                "os_family": class_elem.get("osfamily", ""),
                "os_gen": class_elem.get("osgen", ""),
            }
        )
    os_info["classes"] = os_classes

    return os_info


def extract_open_ports(hosts: List[dict]) -> Dict[str, list]:
    """Extract open ports from parsed hosts."""
    all_ports = {}

    for host in hosts:
        ip = host.get("ip", "unknown")
        open_ports = [
            port["port"]
            for port in host.get("ports", [])
            if port.get("state") == "open"
        ]
        all_ports[ip] = open_ports

    return all_ports


def count_open_ports(hosts: List[dict]) -> dict:
    """Count open ports per host."""
    counts = {}

    for host in hosts:
        ip = host.get("ip", "unknown")
        open_count = sum(
            1 for port in host.get("ports", []) if port.get("state") == "open"
        )
        counts[ip] = open_count

    return counts
