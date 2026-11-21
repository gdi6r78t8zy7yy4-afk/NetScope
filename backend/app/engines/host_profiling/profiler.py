# NetScope Host Profiler

"""
Host profiling engine that aggregates information from multiple sources.
"""

from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class HostProfiler:
    """
    Create comprehensive host profiles by aggregating data from
    multiple sources (discovery, scanning, fingerprinting).
    """

    # Common port-to-service mappings for fallback
    COMMON_PORTS = {
        21: "ftp",
        22: "ssh",
        23: "telnet",
        25: "smtp",
        53: "domain",
        80: "http",
        110: "pop3",
        143: "imap",
        443: "https",
        445: "microsoft-ds",
        993: "imaps",
        995: "pop3s",
        1433: "ms-sql-s",
        1521: "oracle",
        3306: "mysql",
        3389: "ms-term-serv",
        5432: "postgresql",
        5900: "vnc",
        8080: "http-proxy",
    }

    def __init__(self):
        self.logger = logger.bind(profiler="host")

    async def create_profile(
        self,
        ip_address: str,
        discovery_data: Optional[Dict] = None,
        scan_data: Optional[Dict] = None,
        os_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a comprehensive host profile.

        Args:
            ip_address: Target IP
            discovery_data: Network discovery information
            scan_data: Port scan results
            os_data: OS fingerprinting data

        Returns:
            Complete host profile
        """
        self.logger.info("Creating host profile", ip=ip_address)

        profile = {
            "ip_address": ip_address,
            "mac_address": None,
            "hostname": None,
            "device_type": "unknown",
            "operating_system": "unknown",
            "os_version": None,
            "vendor": None,
            "confidence_level": 0.0,
            "network_interfaces": [],
            "open_ports": [],
            "services": [],
            "os_fingerprint": os_data or {},
            "scan_summary": {},
        }

        # Merge discovery data
        if discovery_data:
            profile["mac_address"] = discovery_data.get("mac_address")
            profile["hostname"] = discovery_data.get("hostname")
            profile["vendor"] = discovery_data.get("vendor")

        # Merge scan data
        if scan_data:
            profile["open_ports"] = scan_data.get("open_ports", [])
            profile["services"] = self._process_services(
                scan_data.get(
                    "services_detected", []), scan_data.get(
                    "open_ports", [])
            )

            # Calculate port statistics
            profile["scan_summary"] = {
                "ports_scanned": scan_data.get("ports_scanned", 0),
                "open_ports_count": len(scan_data.get("open_ports", [])),
                "services_found": scan_data.get("total_services", 0),
            }

        # Merge OS data
        if os_data:
            profile["operating_system"] = os_data.get("os_name", "unknown")
            profile["device_type"] = os_data.get(
                "device_type", profile["device_type"])
            profile["os_fingerprint"] = os_data

        # Calculate confidence
        profile["confidence_level"] = self._calculate_confidence(profile)

        return profile

    def _process_services(
        self, services: List[Dict], open_ports: List[Dict]
    ) -> List[Dict]:
        """Process and normalize service information."""
        processed = []

        # Create port lookup
        port_lookup = {p["port"]: p for p in open_ports}

        for service in services:
            port = service.get("port")

            if port and port not in port_lookup:
                continue

            processed.append(
                {
                    "port": port,
                    "service": service.get("service"),
                    "product": service.get("product"),
                    "version": service.get("version"),
                    "confidence": service.get("confidence", 0.5),
                    "method": service.get("method"),
                }
            )

        return processed

    def _calculate_confidence(self, profile: Dict) -> float:
        """Calculate overall confidence score."""
        confidence = 0.0
        factors = 0

        # MAC address presence
        if profile.get("mac_address"):
            confidence += 0.2
            factors += 1

        # Hostname presence
        if profile.get("hostname"):
            confidence += 0.15
            factors += 1

        # Vendor presence
        if profile.get("vendor"):
            confidence += 0.2
            factors += 1

        # OS detection confidence
        if profile.get("operating_system") != "unknown":
            confidence += 0.25
            factors += 1

        # Service detection count
        service_count = len(profile.get("services", []))
        confidence += min(0.2, service_count * 0.05)

        # Normalize
        if factors > 0:
            confidence = min(1.0, confidence)

        return round(confidence, 2)

    async def enrich_profile(self, ip_address: str,
                             existing_profile: Dict) -> Dict:
        """
        Enrich an existing profile with additional data.

        Args:
            ip_address: Target IP
            existing_profile: Existing profile to enrich

        Returns:
            Enriched profile
        """
        self.logger.info("Enriching host profile", ip=ip_address)

        # Re-generate with available data
        return await self.create_profile(ip_address)

    async def get_device_type(self, profile: Dict) -> str:
        """
        Determine device type from profile.

        Args:
            profile: Host profile

        Returns:
            Device type string
        """
        os = profile.get("operating_system", "").lower()

        if "windows" in os:
            return "Windows"
        elif "linux" in os:
            # Check for server indicators
            services = profile.get("services", [])
            service_names = [s.get("service", "") for s in services]

            if "mysql" in service_names or "postgresql" in service_names:
                return "Linux Server"
            elif "http" in service_names or "https" in service_names:
                return "Linux Web Server"
            else:
                return "Linux"
        elif "macos" in os or "darwin" in os:
            return "macOS"
        elif "bsd" in os:
            return "BSD"

        # Use port patterns to guess
        ports = profile.get("open_ports", [])
        service_names = [s.get("service", "") for s in ports]

        if 22 in ports and 80 in ports:
            return "Linux Server"
        elif 3389 in ports:
            return "Windows Desktop"
        elif 445 in ports:
            return "Windows Server" if len(ports) > 10 else "Windows Desktop"

        return "unknown"

    async def get_network_interfaces(self, profile: Dict) -> List[Dict]:
        """
        Extract network interfaces from profile.

        Args:
            profile: Host profile

        Returns:
            List of network interface information
        """
        interfaces = []

        # Base on MAC address if available
        mac = profile.get("mac_address")
        ip = profile.get("ip_address")

        if mac and ip:
            interfaces.append(
                {"mac_address": mac, "ip_address": ip, "interface_type": "ethernet"}
            )

        # Add any discovered interfaces
        for interface in profile.get("network_interfaces", []):
            interfaces.append(interface)

        return interfaces

    async def analyze_services(self, profile: Dict) -> Dict:
        """
        Analyze services in a host profile.

        Args:
            profile: Host profile

        Returns:
            Service analysis
        """
        services = profile.get("services", [])

        # Categorize services
        web_services = []
        database_services = []
        file_services = []
        remote_access = []

        for service in services:
            name = service.get("service", "").lower()

            if "http" in name or "nginx" in name:
                web_services.append(service)
            elif "sql" in name or "mysql" in name or "postgresql" in name:
                database_services.append(service)
            elif "ftp" in name or "smb" in name:
                file_services.append(service)
            elif "ssh" in name or "rdp" in name:
                remote_access.append(service)

        return {
            "total_services": len(services),
            "web_services": web_services,
            "database_services": database_services,
            "file_services": file_services,
            "remote_access": remote_access,
        }
