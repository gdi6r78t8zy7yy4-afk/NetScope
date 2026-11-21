# NetScope Passive Discovery Engine

"""
Passive discovery engine for monitoring network traffic.
"""

from app.core.process_manager import run_command
import asyncio
from typing import List, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class PassiveDiscoveryEngine:
    """
    Passive discovery engine that monitors existing network traffic
    to identify hosts without active scanning.
    """

    def __init__(self):
        self.logger = logger.bind(engine="passive_discovery")

    async def discover_from_arp_table(self) -> List[Dict]:
        """
        Parse ARP table to discover active hosts.

        Returns:
            List of discovered host information
        """
        self.logger.info("Discovering hosts from ARP table")

        # On macOS, use `arp -a` command
        result = await run_command(["arp", "-a"], timeout=30)

        # Handle empty output or error cases
        if result["returncode"] == 0:
            return self._parse_arp_output(result["stdout"])
        elif result.get("file_not_found"):
            self.logger.error("ARP command not found")
            return []
        else:
            self.logger.warning(
                "ARP command failed",
                stderr=result.get(
                    "stderr",
                    ""))
            return []

    def _parse_arp_output(self, output: str) -> List[Dict]:
        """Parse ARP table output."""
        hosts = []

        for line in output.strip().split("\n"):
            if not line:
                continue

            # Parse ARP table format
            # e.g., "router (192.168.1.1) at 00:11:22:33:44:55 [ether] on en0"
            try:
                parts = line.split()

                if len(parts) >= 4:
                    hostname = parts[0].rstrip(":")
                    ip_address = parts[1].strip("()")
                    mac_address = parts[3]

                    hosts.append(
                        {
                            "ip_address": ip_address,
                            "mac_address": mac_address.upper(),
                            "hostname": (
                                hostname if hostname != "(incomplete)" else None
                            ),
                        }
                    )

            except Exception as e:
                self.logger.warning("Failed to parse ARP line", error=str(e))
                continue

        return hosts

    async def discover_from_llmnr(self) -> List[Dict]:
        """
        Attempt LLMNR (Link-local Multicast Name Resolution)
        to discover hosts.

        Returns:
            List of discovered host information
        """
        self.logger.info("Attempting LLMNR discovery")

        # macOS doesn't have a direct way to query LLMNR
        # This would require specialized libraries or nmap scripts

        return []

    async def discover_from_mdns(self) -> List[Dict]:
        """
        Attempt mDNS (multicast DNS) discovery.

        Returns:
            List of discovered host information
        """
        self.logger.info("Attempting mDNS discovery")

        # Use `dns-sd` command on macOS
        result = await run_command(
            ["dns-sd", "-B", "_services._dns-sd._udp", "local"], timeout=30
        )

        # Handle empty output or error cases
        if result["returncode"] == 0:
            return self._parse_mdns_output(result["stdout"])
        elif result.get("file_not_found"):
            self.logger.error("dns-sd command not found")
            return []
        else:
            # Non-fatal error, return empty list
            return []

    def _parse_mdns_output(self, output: str) -> List[Dict]:
        """Parse mDNS output."""
        services = []

        for line in output.strip().split("\n"):
            if "B" in line and "local." in line:
                parts = line.split()
                if len(parts) >= 5:
                    services.append(
                        {"service_type": parts[0], "name": parts[2]})

        return services

    async def discover_from_netstat(self) -> List[Dict]:
        """
        Parse netstat to find active connections.

        Returns:
            List of discovered host information
        """
        self.logger.info("Discovering hosts from netstat")

        result = await run_command(["netstat", "-an"], timeout=30)

        # Handle empty output or error cases
        if result["returncode"] == 0:
            return self._parse_netstat_output(result["stdout"])
        elif result.get("file_not_found"):
            self.logger.error("netstat command not found")
            return []
        else:
            # Non-fatal error, return empty list
            return []

    def _parse_netstat_output(self, output: str) -> List[Dict]:
        """Parse netstat output."""
        hosts = set()

        for line in output.strip().split("\n"):
            if "ESTABLISHED" in line or "SYN_SENT" in line:
                # Extract remote addresses
                parts = line.split()
                if len(parts) >= 5:
                    remote_addr = parts[4]
                    # Extract IP from address (e.g., "192.168.1.1.445")
                    if "." in remote_addr:
                        ip = remote_addr.split(".")[0]
                        if self._is_valid_ip(ip):
                            hosts.add(ip)

        return [{"ip_address": ip} for ip in list(hosts)]

    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IPv4 address."""
        parts = ip.split(".")
        if len(parts) != 4:
            return False

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except ValueError:
            return False

    async def run_passive_scan(self) -> Dict:
        """
        Run all passive discovery methods.

        Returns:
            Discovery results
        """
        self.logger.info("Starting passive discovery scan")

        tasks = [self.discover_from_arp_table(), self.discover_from_netstat()]

        results = await asyncio.gather(*tasks)

        all_hosts = []
        for result in results:
            all_hosts.extend(result)

        # Deduplicate
        unique_hosts = []
        seen_ips = set()

        for host in all_hosts:
            ip = host.get("ip_address")
            if ip and ip not in seen_ips:
                unique_hosts.append(host)
                seen_ips.add(ip)

        return {
            "discovery_method": "passive",
            "hosts_found": len(unique_hosts),
            "hosts": unique_hosts,
        }
