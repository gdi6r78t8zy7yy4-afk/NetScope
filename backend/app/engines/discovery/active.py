# NetScope Active Discovery Engine

"""
Active discovery engine using Nmap and ARP-scan.
"""

import asyncio
from typing import List, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

from app.core.process_manager import run_command


class ActiveDiscoveryEngine:
    """
    Active discovery engine that probes networks to discover hosts.
    Uses Nmap ping scan for reliable host detection.
    """
    
    def __init__(
        self,
        max_concurrent_hosts: int = 5,
        scan_timeout: int = 60
    ):
        self.max_concurrent_hosts = max_concurrent_hosts
        self.scan_timeout = scan_timeout
        self.logger = logger.bind(engine="active_discovery")
    
    async def discover_with_nmap(
        self,
        target: str,
        rate_limit: str = "medium"
    ) -> Dict:
        """
        Discover hosts using Nmap ping scan.
        
        Args:
            target: Target IP or CIDR range
            rate_limit: Scan speed preset
            
        Returns:
            Discovery results
        """
        self.logger.info(
            "Starting Nmap discovery",
            target=target,
            rate_limit=rate_limit
        )
        
        # Log debug info about the target
        self.logger.debug("Discovery target details", target=target, rate_limit=rate_limit)
        
        # Determine Nmap arguments based on rate limit
        speed_args = self._get_speed_args(rate_limit)
        
        # Ping scan (no port scan) with aggressive timing
        cmd = [
            "nmap",
            "-sn",  # Ping scan
            *speed_args,
            target
        ]
        
        result = await run_command(cmd, timeout=self.scan_timeout)
        
        self.logger.debug(
            "Nmap command completed",
            returncode=result.get("returncode"),
            stdout_length=len(result.get("stdout", "")) if result.get("stdout") else 0,
            stderr_length=len(result.get("stderr", "")) if result.get("stderr") else 0
        )
        
        if result["returncode"] == 0:
            self.logger.info("Nmap scan completed successfully")
            return self._parse_nmap_output(result["stdout"])
        elif result.get("timed_out"):
            self.logger.error("Nmap scan timed out", target=target)
            return {"error": "Scan timeout", "hosts_found": 0}
        elif result.get("file_not_found"):
            self.logger.error("Nmap not found", cmd=cmd)
            return {"error": "Nmap not installed", "hosts_found": 0}
        else:
            self.logger.error(
                "Nmap scan failed",
                stderr=result.get("stderr", ""),
                return_code=result.get("returncode")
            )
            return {"error": "Nmap scan failed", "hosts_found": 0}
    
    def _get_speed_args(self, rate_limit: str) -> List[str]:
        """Get Nmap timing arguments based on rate limit."""
        presets = {
            "slow": ["-T1", "--min-hostgroup", "5"],
            "medium": ["-T2", "--min-hostgroup", "10"],
            "fast": ["-T3", "--min-hostgroup", "50"],
            "aggressive": ["-T4", "--min-hostgroup", "100"]
        }
        
        return presets.get(rate_limit, ["-T2", "--min-hostgroup", "10"])
    
    def _parse_nmap_output(self, output: str) -> Dict:
        """Parse Nmap discovery output."""
        self.logger.debug("Parsing Nmap discovery output", output_length=len(output))
        
        hosts = []
        
        current_host = {}
        
        for line in output.split("\n"):
            # Parse Nmap scan report lines
            if "Nmap scan report for" in line:
                # Save previous host if exists
                if current_host:
                    hosts.append(current_host)
                
                current_host = {}
                
                # Extract IP and hostname
                parts = line.split("for ")
                if len(parts) > 1:
                    host_info = parts[1].strip()
                    
                    # IP might be in parentheses
                    if "(" in host_info and ")" in host_info:
                        parts = host_info.split(" (")
                        current_host["ip_address"] = parts[1].rstrip(")")
                        current_host["hostname"] = parts[0]
                    else:
                        current_host["ip_address"] = host_info
                
                self.logger.debug("Found Nmap scan report", ip=current_host.get("ip_address"))
            
            elif "MAC Address:" in line:
                parts = line.split("MAC Address: ")
                if len(parts) > 1:
                    mac_info = parts[1].strip()
                    
                    # Extract MAC and vendor
                    if " (" in mac_info:
                        parts = mac_info.split(" (")
                        current_host["mac_address"] = parts[0]
                        current_host["vendor"] = (
                            parts[1].rstrip(")")
                            if len(parts) > 1 else None
                        )
                    else:
                        current_host["mac_address"] = mac_info
                
                self.logger.debug("Found MAC address", mac=current_host.get("mac_address"))
            
            elif "Host is up" in line:
                current_host["status"] = "up"
                self.logger.debug("Host detected as up", ip=current_host.get("ip_address"))
            
            elif "Latency:" in line:
                # Extract latency if available
                pass
        
        # Don't forget the last host
        if current_host:
            hosts.append(current_host)
        
        # Filter to only hosts with IP addresses
        valid_hosts = [h for h in hosts if "ip_address" in h]
        
        self.logger.info(
            "Nmap discovery parsing complete",
            total_hosts=len(hosts),
            valid_hosts_found=len(valid_hosts)
        )
        
        return {
            "discovery_method": "active_nmap",
            "hosts_found": len(valid_hosts),
            "hosts": valid_hosts
        }
    
    async def discover_with_arp_scan(
        self,
        subnet: str,
        interface: Optional[str] = None
    ) -> Dict:
        """
        Discover hosts using ARP scan.
        
        Args:
            subnet: Subnet to scan
            interface: Network interface to use
            
        Returns:
            Discovery results
        """
        self.logger.info("Starting ARP scan", subnet=subnet)
        
        cmd = ["arp-scan", subnet]
        
        if interface:
            cmd.extend(["-I", interface])
        
        try:
            result = await run_command(cmd, timeout=self.scan_timeout)
            
            if result["returncode"] == 0:
                return self._parse_arp_scan_output(result["stdout"])
            else:
                # ARP scan might fail without root privileges
                self.logger.warning("ARP-scan failed, try with sudo")
                return {"error": "ARP scan requires elevated privileges", "hosts_found": 0}
                
        except FileNotFoundError:
            self.logger.error("ARP-scan not found")
            return {"error": "ARP-scan not installed"}
            
        except asyncio.TimeoutError:
            self.logger.error("ARP scan timed out")
            return {"error": "Scan timeout"}
    
    def _parse_arp_scan_output(self, output: str) -> Dict:
        """Parse ARP scan output."""
        hosts = []
        
        for line in output.split("\n"):
            if not line.strip():
                continue
            
            parts = line.split()
            
            # Skip header and footer lines
            if len(parts) >= 2 and ":" in parts[1]:
                ip = parts[0]
                mac = parts[1].upper()
                
                hosts.append({
                    "ip_address": ip,
                    "mac_address": mac
                })
        
        return {
            "discovery_method": "active_arp_scan",
            "hosts_found": len(hosts),
            "hosts": hosts
        }
    
    async def discover_interfaces(self) -> List[Dict]:
        """
        Discover local network interfaces.
        
        Returns:
            List of interface information
        """
        self.logger.info("Discovering network interfaces")
        
        try:
            result = await run_command(["networksetup", "-listallhardwareports"], timeout=30)
            
            if result["returncode"] == 0:
                return self._parse_interfaces_output(result["stdout"])
            else:
                # Fall back to `ifconfig`
                return await self._discover_with_ifconfig()
                
        except FileNotFoundError:
            return await self._discover_with_ifconfig()
    
    def _parse_interfaces_output(self, output: str) -> List[Dict]:
        """Parse networksetup output."""
        interfaces = []
        
        current_interface = {}
        
        for line in output.split("\n"):
            if "Device:" in line:
                if current_interface:
                    interfaces.append(current_interface)
                
                current_interface = {
                    "interface": line.split(":")[1].strip()
                }
            
            elif "Port:" in line:
                # Skip "Hardware Port:" lines, they're handled separately
                if not line.startswith("Hardware Port:"):
                    current_interface["port"] = line.split(":")[1].strip()
            
            elif "Hardware Port:" in line:
                current_interface["hardware_port"] = (
                    line.split(":")[1].strip()
                )
            
            elif "Ethernet Address:" in line:
                # Parse from the end to avoid partial matches
                current_interface["mac_address"] = (
                    line.split("Ethernet Address:")[1].strip()
                )
            
            elif "Status:" in line:
                current_interface["status"] = (
                    line.split(":")[1].strip()
                )
        
        if current_interface:
            interfaces.append(current_interface)
        
        return interfaces
    
    async def _discover_with_ifconfig(self) -> List[Dict]:
        """Discover interfaces using ifconfig."""
        try:
            result = await run_command(["ifconfig"], timeout=30)
            
            if result["returncode"] == 0:
                return self._parse_ifconfig_output(result["stdout"])
            
        except FileNotFoundError:
            pass
        
        return []
    
    def _parse_ifconfig_output(self, output: str) -> List[Dict]:
        """Parse ifconfig output."""
        interfaces = []
        
        # Split by interface blocks
        blocks = output.split("\n\n")
        
        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue
            
            current_interface = {"interface": lines[0].split(":")[0]}
            
            for line in lines:
                if "ether" in line.lower():
                    # MAC address
                    parts = line.split()
                    for part in parts:
                        if ":" in part and len(part) == 17:
                            current_interface["mac_address"] = part.upper()
                            break
                
                elif "status:" in line.lower():
                    current_interface["status"] = (
                        line.split(":")[1].strip()
                    )
                
                elif "inet " in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_interface["ip_address"] = parts[1]
                
                elif "media:" in line.lower():
                    current_interface["media"] = (
                        line.split(":", 1)[1].strip()
                    )
            
            if current_interface.get("ip_address"):
                interfaces.append(current_interface)
        
        return interfaces
    
    async def discover_gateways(self) -> List[Dict]:
        """
        Discover network gateways.
        
        Returns:
            List of gateway information
        """
        self.logger.info("Discovering gateways")
        
        try:
            result = await run_command(["netstat", "-rn"], timeout=30)
            
            if result["returncode"] == 0:
                return self._parse_gateways_output(result["stdout"])
            
        except FileNotFoundError:
            pass
        
        return []
    
    def _parse_gateways_output(self, output: str) -> List[Dict]:
        """Parse netstat routing table."""
        gateways = []
        
        for line in output.split("\n"):
            if "default" in line and "UGSc" in line:
                parts = line.split()
                
                if len(parts) >= 2:
                    gateway = {
                        "ip_address": parts[1],
                        "interface": parts[-1] if len(parts) > 2 else None
                    }
                    gateways.append(gateway)
        
        return gateways
    
    async def run_active_scan(self, targets: List[str]) -> Dict:
        """
        Run active discovery on multiple targets.
        
        Args:
            targets: List of IP addresses or CIDR ranges
            
        Returns:
            Discovery results
        """
        self.logger.info(
            "Starting active discovery",
            targets=targets,
            concurrent_hosts=self.max_concurrent_hosts
        )
        
        results = []
        
        # Discover local interfaces first
        interfaces = await self.discover_interfaces()
        results.append({
            "type": "interfaces",
            "data": interfaces
        })
        
        # Discover gateways
        gateways = await self.discover_gateways()
        results.append({
            "type": "gateways",
            "data": gateways
        })
        
        # Discover hosts in targets
        for target in targets:
            result = await self.discover_with_nmap(target)
            results.append({
                "type": "hosts",
                "data": result
            })
        
        return {
            "discovery_method": "active",
            "results": results
        }
