# NetScope Base Port Scanner

"""
Base port scanner interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class PortScanner(ABC):
    """Base interface for port scanners."""

    @abstractmethod
    async def scan_single_port(
        self, ip_address: str, port: int, protocol: str = "tcp"
    ) -> Dict:
        """
        Scan a single port.

        Args:
            ip_address: Target IP
            port: Port number
            protocol: Protocol (tcp/udp)

        Returns:
            Port scan result
        """
        pass

    @abstractmethod
    async def scan_ports(
        self, ip_address: str, ports: List[int], protocol: str = "tcp"
    ) -> Dict:
        """
        Scan multiple ports.

        Args:
            ip_address: Target IP
            ports: List of port numbers
            protocol: Protocol

        Returns:
            Scan results
        """
        pass

    @abstractmethod
    async def scan_port_range(
        self, ip_address: str, start_port: int, end_port: int, protocol: str = "tcp"
    ) -> Dict:
        """
        Scan a range of ports.

        Args:
            ip_address: Target IP
            start_port: First port to scan
            end_port: Last port to scan
            protocol: Protocol

        Returns:
            Scan results
        """
        pass

    @abstractmethod
    async def scan_common_ports(
            self, ip_address: str, protocol: str = "tcp") -> Dict:
        """
        Scan common ports.

        Args:
            ip_address: Target IP
            protocol: Protocol

        Returns:
            Scan results
        """
        pass

    @abstractmethod
    async def full_scan(self, ip_address: str, protocol: str = "tcp") -> Dict:
        """
        Full TCP scan (ports 1-65535).

        Args:
            ip_address: Target IP
            protocol: Protocol (tcp)

        Returns:
            Scan results
        """
        pass
