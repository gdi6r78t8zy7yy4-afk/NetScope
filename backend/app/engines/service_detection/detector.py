# NetScope Service Detector

"""
Service detection engine using Nmap service fingerprinting.
"""

from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ServiceDetector:
    """
    Detect services on open ports using Nmap service fingerprinting.
    """
    
    # Common port to service mappings (fallback when Nmap detection fails)
    COMMON_SERVICES = {
        21: {"service": "ftp", "protocol": "tcp"},
        22: {"service": "ssh", "protocol": "tcp"},
        23: {"service": "telnet", "protocol": "tcp"},
        25: {"service": "smtp", "protocol": "tcp"},
        53: {"service": "domain", "protocol": "udp"},
        80: {"service": "http", "protocol": "tcp"},
        110: {"service": "pop3", "protocol": "tcp"},
        143: {"service": "imap", "protocol": "tcp"},
        443: {"service": "https", "protocol": "tcp"},
        445: {"service": "microsoft-ds", "protocol": "tcp"},
        993: {"service": "imaps", "protocol": "tcp"},
        995: {"service": "pop3s", "protocol": "tcp"},
        1433: {"service": "ms-sql-s", "protocol": "tcp"},
        1521: {"service": "oracle", "protocol": "tcp"},
        3306: {"service": "mysql", "protocol": "tcp"},
        3389: {"service": "ms-term-serv", "protocol": "tcp"},
        5432: {"service": "postgresql", "protocol": "tcp"},
        5900: {"service": "vnc", "protocol": "tcp"},
        6379: {"service": "redis", "protocol": "tcp"},
        8080: {"service": "http-proxy", "protocol": "tcp"},
        8443: {"service": "https-alt", "protocol": "tcp"},
        27017: {"service": "mongod", "protocol": "tcp"},
    }
    
    def __init__(self):
        self.logger = logger.bind(detector="service")
    
    async def detect_services(
        self,
        ip_address: str,
        ports: List[Dict]
    ) -> Dict:
        """
        Detect services on a list of open ports.
        
        Args:
            ip_address: Target IP
            ports: List of port information
            
        Returns:
            Service detection results
        """
        self.logger.info(
            "Detecting services",
            ip=ip_address,
            port_count=len(ports)
        )
        
        results = {
            "ip_address": ip_address,
            "services_detected": [],
            "total_services": 0
        }
        
        for port_info in ports:
            detection = await self.detect_service(
                ip_address,
                port_info
            )
            
            if detection:
                results["services_detected"].append(detection)
        
        results["total_services"] = len(results["services_detected"])
        
        return results
    
    async def detect_service(
        self,
        ip_address: str,
        port_info: Dict
    ) -> Optional[Dict]:
        """
        Detect service on a single port.
        
        Args:
            ip_address: Target IP
            port_info: Port information dictionary
            
        Returns:
            Service detection result or None if failed
        """
        port = port_info.get("port")
        
        # Check common services first (fast path)
        if port in self.COMMON_SERVICES:
            return {
                "ip_address": ip_address,
                "port": port,
                **self.COMMON_SERVICES[port],
                "method": "fallback",
                "confidence": 0.8
            }
        
        # Try Nmap service detection (slow path)
        nmap_result = await self._nmap_service_detection(ip_address, port)
        
        if nmap_result:
            return {
                "ip_address": ip_address,
                "port": port,
                **nmap_result,
                "method": "nmap",
                "confidence": 0.9
            }
        
        return None
    
    async def _nmap_service_detection(
        self,
        ip_address: str,
        port: int
    ) -> Optional[Dict]:
        """
        Use Nmap for service detection.
        
        Args:
            ip_address: Target IP
            port: Port number
            
        Returns:
            Nmap service detection result
        """
        cmd = [
            "nmap",
            "-sV",  # Service version detection
            "-p", str(port),
            "-T4",
            ip_address
        ]
        
        try:
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            if process.returncode == 0:
                return self._parse_nmap_service_output(stdout.decode())
            
        except Exception as e:
            self.logger.warning("Nmap service detection failed", error=str(e))
        
        return None
    
    def _parse_nmap_service_output(self, output: str) -> Optional[Dict]:
        """Parse Nmap service detection output."""
        for line in output.split("\n"):
            if "/" in line and not "PORT" in line:
                parts = line.split()
                
                if len(parts) >= 3:
                    return {
                        "service": parts[2],
                        "protocol": parts[0].split("/")[1] if "/" in parts[0] else "tcp",
                        "method": "nmap_service"
                    }
        
        return None
    
    async def detect_banner(
        self,
        ip_address: str,
        port: int,
        protocol: str = "tcp"
    ) -> Optional[str]:
        """
        Detect service banner.
        
        Args:
            ip_address: Target IP
            port: Port number
            protocol: Protocol
            
        Returns:
            Service banner or None
        """
        # Use Nmap with version-all for detailed banners
        cmd = [
            "nmap",
            "-sV",
            "--version-all",
            "-p", str(port),
            ip_address
        ]
        
        try:
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            if process.returncode == 0:
                return self._extract_banner(stdout.decode())
            
        except Exception as e:
            self.logger.warning("Banner detection failed", error=str(e))
        
        return None
    
    def _extract_banner(self, output: str) -> Optional[str]:
        """Extract banner from Nmap output."""
        for line in output.split("\n"):
            if "Version:" in line or "Product:" in line:
                return line.strip()
        
        return None
    
    async def get_service_version(
        self,
        ip_address: str,
        port: int
    ) -> Dict:
        """
        Get detailed service version information.
        
        Args:
            ip_address: Target IP
            port: Port number
            
        Returns:
            Service version information
        """
        self.logger.info("Getting service version", ip=ip_address, port=port)
        
        result = {
            "ip_address": ip_address,
            "port": port,
            "service": None,
            "product": None,
            "version": None,
            "extra_info": None
        }
        
        # Use Nmap for version detection
        cmd = [
            "nmap",
            "-sV",
            "-p", str(port),
            ip_address
        ]
        
        try:
            import asyncio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            if process.returncode == 0:
                result = self._parse_version_output(stdout.decode())
        
        except Exception as e:
            self.logger.error("Version detection failed", error=str(e))
        
        return result
    
    def _parse_version_output(self, output: str) -> Dict:
        """Parse Nmap version detection output."""
        result = {
            "ip_address": None,
            "port": None,
            "service": None,
            "product": None,
            "version": None,
            "extra_info": None
        }
        
        for line in output.split("\n"):
            if "Product:" in line:
                # e.g., "Product: Apache httpd"
                parts = line.split("Product:")
                if len(parts) > 1:
                    result["product"] = parts[1].strip()
            
            elif "Version:" in line:
                # e.g., "Version: 2.4.51"
                parts = line.split("Version:")
                if len(parts) > 1:
                    result["version"] = parts[1].strip()
            
            elif "Extra" in line:
                # e.g., "Extra: HTTP methods"
                parts = line.split("Extra:", 1)
                if len(parts) > 1:
                    result["extra_info"] = parts[1].strip()
        
        return result
    
    async def detect_all_services(
        self,
        ip_address: str
    ) -> Dict:
        """
        Detect all services on an IP address.
        
        Args:
            ip_address: Target IP
            
        Returns:
            All service detection results
        """
        self.logger.info("Detecting all services", ip=ip_address)
        
        # First, do a port scan to find open ports
        from app.engines.port_scanner.nmap_engine import NmapPortScanner
        
        scanner = NmapPortScanner()
        
        # Scan common ports first
        result = await scanner.scan_common_ports(ip_address)
        
        # If open ports found, detect services
        if result.get("open_ports"):
            detector = ServiceDetector()
            
            return await self.detect_services(
                ip_address,
                result["open_ports"]
            )
        
        return {
            "ip_address": ip_address,
            "services_detected": [],
            "total_services": 0
        }
