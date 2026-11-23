# NetScope Nmap Port Scanner

"""
Nmap-based port scanner implementation.

Phase 5: Consolidate Nmap Integration
- All scans use structured XML output with -oX -
- Parse results using existing parser (parse_nmap_xml)
- Preserve raw XML as scan evidence
"""

from app.core.process_manager import ProcessManager, run_command
import asyncio
from typing import List, Dict, Optional
import logging

import structlog

logger = structlog.get_logger(__name__)


class NmapPortScanner:
    """
    Port scanner using Nmap as the backend.

    All scan methods now use XML output (-oX -) for structured parsing
    and evidence preservation.

    Features:
    - Concurrency control using semaphores to limit parallel scans
    - Rate limiting between consecutive scans
    - Process termination on cancellation
    """

    # Class-level semaphore for concurrent scan control
    _scan_semaphore: Optional[asyncio.Semaphore] = None
    _max_concurrent_scans = 5
    _last_scan_time: Optional[float] = None
    _scan_cooldown = 0.1  # Seconds between scans to avoid overwhelming system

    COMMON_PORTS = [
        21,  # FTP
        22,  # SSH
        23,  # Telnet
        25,  # SMTP
        53,  # DNS
        80,  # HTTP
        110,  # POP3
        143,  # IMAP
        443,  # HTTPS
        445,  # SMB
        993,  # IMAPS
        995,  # POP3S
        1433,  # MSSQL
        1521,  # Oracle
        3306,  # MySQL
        3389,  # RDP
        5432,  # PostgreSQL
        5900,  # VNC
        8080,  # HTTP Alt
        8443,  # HTTPS Alt
    ]

    def __init__(self, timeout: int = 60, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.process_manager = ProcessManager(timeout=timeout)
        self.logger = logger.bind(scanner="nmap")

        # Initialize semaphore if not already set
        if NmapPortScanner._scan_semaphore is None:
            NmapPortScanner._scan_semaphore = asyncio.Semaphore(
                self._max_concurrent_scans
            )

        # Track running processes for cancellation support
        self._running_processes: Dict[int, asyncio.Task] = {}

    @classmethod
    def set_max_concurrent_scans(cls, count: int):
        """Set the maximum number of concurrent scans."""
        cls._max_concurrent_scans = count
        cls._scan_semaphore = asyncio.Semaphore(count)
        logger.info(
            "Nmap concurrency limit updated",
            max_concurrent_scans=count)

    @classmethod
    def get_semaphore(cls) -> asyncio.Semaphore:
        """Get the scan semaphore for external use."""
        if cls._scan_semaphore is None:
            cls._scan_semaphore = asyncio.Semaphore(cls._max_concurrent_scans)
        return cls._scan_semaphore

    async def _acquire_scan_lock(self):
        """Acquire scan semaphore with rate limiting."""
        await self._scan_semaphore.acquire()

        # Apply cooldown between scans
        if self._last_scan_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_scan_time
            if elapsed < self._scan_cooldown:
                wait_time = self._scan_cooldown - elapsed
                logger.info("Rate limiting scan", wait_time=wait_time)
                await asyncio.sleep(wait_time)

        self._last_scan_time = asyncio.get_event_loop().time()

    async def _release_scan_lock(self):
        """Release scan semaphore."""
        if self._scan_semaphore is not None:
            self._scan_semaphore.release()

    def _parse_scan_output(
            self, output: str, ip_address: str, port: int) -> Dict:
        """Parse single port scan output."""
        result = {
            "ip_address": ip_address,
            "port": port,
            "protocol": "tcp",
            "state": "unknown",
            "service": None,
            "error": None,
        }

        lines = output.split("\n")
        for line in lines:
            if f"{port}/" in line and "PORT" not in line:
                parts = line.split()
                if len(parts) >= 2:
                    result["state"] = parts[1]
                    if len(parts) > 2:
                        result["service"] = parts[2]
                break

        return result

    def _parse_multi_port_output(
        self, output: str, ip_address: str, ports: List[int]
    ) -> Dict:
        """Parse multi-port scan output."""
        result = {
            "ip_address": ip_address,
            "ports_scanned": len(ports),
            "open_ports": [],
            "closed_ports": [],
            "filtered_ports": [],
        }

        for line in output.split("\n"):
            if "/" in line and "PORT" not in line:
                parts = line.split()

                if len(parts) >= 2:
                    try:
                        port_num = int(parts[0].split("/")[0])

                        if port_num in ports:
                            state = parts[1]
                            result[f"{state}_ports"].append(
                                {"port": port_num, "state": state}
                            )
                    except ValueError:
                        continue

        return result

    def _parse_range_output(
        self, output: str, ip_address: str, start_port: int, end_port: int
    ) -> Dict:
        """Parse port range scan output."""
        result = {
            "ip_address": ip_address,
            "port_range": f"{start_port}-{end_port}",
            "open_ports": [],
            "closed_ports": [],
            "filtered_ports": [],
        }

        for line in output.split("\n"):
            if "/" in line and "PORT" not in line:
                parts = line.split()

                if len(parts) >= 3:
                    port_part = parts[0].split("/")[0]

                    if "-" in port_part:
                        port_range = port_part.split("-")
                        if len(port_range) == 2:
                            try:
                                port_start = int(port_range[0])
                                port_end = int(port_range[1])

                                for p in range(port_start, port_end + 1):
                                    if start_port <= p <= end_port:
                                        result[f"{parts[1]}_ports"].append(
                                            {"port": p, "state": parts[1]}
                                        )
                                    elif p > end_port:
                                        break
                            except ValueError:
                                continue
                    else:
                        try:
                            port_num = int(port_part)

                            if start_port <= port_num <= end_port:
                                state = parts[1]
                                result[f"{state}_ports"].append(
                                    {"port": port_num, "state": state}
                                )
                        except ValueError:
                            continue

        return result

    def _create_xml_command(self, ip_address: str,
                            args: List[str]) -> List[str]:
        """
        Create nmap command with XML output.

        Args:
            ip_address: Target IP address
            args: Additional nmap arguments

        Returns:
            Complete command list with -oX - flag
        """
        cmd = ["nmap", "-Pn", "-oX", "-", *args, ip_address]
        return cmd

    async def scan_single_port(
        self, ip_address: str, port: int, protocol: str = "tcp", scan=None
    ) -> Dict:
        """
        Scan a single port on a target.

        Args:
            ip_address: Target IP
            port: Port number to scan
            protocol: Protocol (tcp/udp)
            scan: Optional Scan model instance for progress tracking

        Returns:
            Scan result dict with raw_xml field
        """
        self.logger.info(
            "Scanning port",
            ip=ip_address,
            port=port,
            protocol=protocol)

        # Acquire scan lock with rate limiting
        await self._acquire_scan_lock()

        try:
            cmd = ["nmap", "-Pn", "-p", str(port)]
            if protocol == "udp":
                cmd.append("-sU")

            # Add XML output to command
            xml_cmd = ["-oX", "-", *cmd[1:], ip_address]

            result = await self._execute_nmap(xml_cmd)

            scan_result = {
                "ip_address": ip_address,
                "port": port,
                "protocol": protocol,
                "state": "unknown",
                "service": None,
                "error": None,
            }

            if result["returncode"] == 0:
                # Parse the text output
                scan_result = self._parse_scan_output(
                    result["stdout"], ip_address, port
                )

                # Store raw XML for evidence
                scan_result["raw_xml"] = result["stdout"]
            else:
                scan_result["error"] = result["stderr"]

            # Update progress during single port scan
            if scan is not None and hasattr(scan, 'progress'):
                # For single port scans, progress increases by 85 per port
                scan.progress = min(scan.progress + 85, 95)

            return scan_result
        finally:
            await self._release_scan_lock()

    async def scan_ports(
        self, ip_address: str, ports: List[int], protocol: str = "tcp", scan=None
    ) -> Dict:
        """
        Scan multiple ports on a target.

        Args:
            ip_address: Target IP
            ports: List of port numbers
            protocol: Protocol (tcp/udp)
            scan: Optional Scan model instance for progress tracking

        Returns:
            Scan result dict with raw_xml field
        """
        self.logger.info(
            "Scanning ports",
            ip=ip_address,
            port_count=len(ports))

        # Acquire scan lock with rate limiting
        await self._acquire_scan_lock()

        try:
            # Join ports with comma
            port_list = ",".join(str(p) for p in ports)

            # Build command with XML output
            cmd = ["nmap", "-Pn", "-p", port_list]
            if protocol == "tcp":
                cmd.append("-sV")
            else:
                cmd.append("-sU")

            # Add XML output to command
            xml_cmd = ["-oX", "-", *cmd[1:], ip_address]

            result = await self._execute_nmap(xml_cmd)

            scan_result = {
                "ip_address": ip_address,
                "ports_scanned": len(ports),
                "open_ports": [],
                "closed_ports": [],
                "filtered_ports": [],
            }

            if result["returncode"] == 0:
                # Parse the text output
                scan_result = self._parse_multi_port_output(
                    result["stdout"], ip_address, ports
                )

                # Store raw XML for evidence
                scan_result["raw_xml"] = result["stdout"]
            else:
                scan_result["error"] = result["stderr"]

            # Update progress during port scan
            if scan is not None and hasattr(scan, 'progress') and ports:
                ports_scanned = len(ports)
                if scan_result.get("open_ports"):
                    ports_scanned += len(scan_result["open_ports"])
                if scan_result.get("closed_ports"):
                    ports_scanned += len(scan_result["closed_ports"])
                
                # Estimate total ports based on scan type (we'll use a multiplier)
                # For common ports scan, assume 20 total; for ranges, use the provided count
                total_ports_estimate = max(ports_scanned * 2, len(ports))
                
                if total_ports_estimate > 0:
                    progress_per_port = (85 / total_ports_estimate) if total_ports_estimate > 0 else 1
                    calculated_progress = min(10 + int((ports_scanned / max(total_ports_estimate, 1)) * 85), 95)
                    scan.progress = calculated_progress

            return scan_result
        finally:
            await self._release_scan_lock()

    async def scan_port_range(
        self, ip_address: str, start_port: int, end_port: int, protocol: str = "tcp", scan=None
    ) -> Dict:
        """
        Scan a range of ports on a target.

        Args:
            ip_address: Target IP
            start_port: First port in range
            end_port: Last port in range
            protocol: Protocol (tcp/udp)
            scan: Optional Scan model instance for progress tracking

        Returns:
            Scan result dict with raw_xml field
        """
        self.logger.info(
            "Scanning port range",
            ip=ip_address,
            start_port=start_port,
            end_port=end_port,
        )

        # Acquire scan lock with rate limiting
        await self._acquire_scan_lock()

        try:
            # Build command with XML output
            cmd = ["nmap", "-Pn", "-p", f"{start_port}-{end_port}"]
            if protocol == "tcp":
                cmd.append("-sV")
            else:
                cmd.append("-sU")

            # Add XML output to command
            xml_cmd = ["-oX", "-", *cmd[1:], ip_address]

            result = await self._execute_nmap(xml_cmd)

            scan_result = {
                "ip_address": ip_address,
                "port_range": f"{start_port}-{end_port}",
                "open_ports": [],
                "closed_ports": [],
                "filtered_ports": [],
            }

            if result["returncode"] == 0:
                # Parse the text output
                scan_result = self._parse_range_output(
                    result["stdout"], ip_address, start_port, end_port
                )

                # Store raw XML for evidence
                scan_result["raw_xml"] = result["stdout"]
            else:
                scan_result["error"] = result["stderr"]

            # Update progress during port range scan
            if scan is not None and hasattr(scan, 'progress'):
                total_ports = end_port - start_port + 1
                ports_scanned = len(scan_result.get("open_ports", [])) + len(scan_result.get("closed_ports", []))
                
                if total_ports > 0:
                    progress_per_port = (85 / total_ports) if total_ports > 0 else 1
                    calculated_progress = min(10 + int((ports_scanned / max(total_ports, 1)) * 85), 95)
                    scan.progress = calculated_progress

            return scan_result
        finally:
            await self._release_scan_lock()

    async def scan_common_ports(self, ip_address: str, scan=None) -> Dict:
        """
        Scan common ports on a target.

        Args:
            ip_address: Target IP
            scan: Optional Scan model instance for progress tracking

        Returns:
            Scan result dict
        """
        return await self.scan_ports(ip_address, self.COMMON_PORTS, scan=scan)

    async def full_scan(self, ip_address: str, scan=None) -> Dict:
        """
        Perform a full TCP port scan (1-65535).

        Args:
            ip_address: Target IP
            scan: Optional Scan model instance for progress tracking

        Returns:
            Scan result dict with raw_xml field
        """
        self.logger.info("Performing full scan", ip=ip_address)

        # Acquire scan lock with rate limiting
        await self._acquire_scan_lock()

        try:
            # Build command with XML output
            cmd = ["nmap", "-Pn", "-p", "1-65535"]

            # Add XML output to command
            xml_cmd = ["-oX", "-", *cmd[1:], ip_address]

            result = await self._execute_nmap(xml_cmd)

            scan_result = {
                "ip_address": ip_address,
                "port_range": "1-65535",
                "open_ports": [],
                "closed_ports": [],
                "filtered_ports": [],
            }

            if result["returncode"] == 0:
                # Parse the text output
                scan_result = self._parse_range_output(
                    result["stdout"], ip_address, 1, 65535
                )

                # Store raw XML for evidence
                scan_result["raw_xml"] = result["stdout"]
            else:
                scan_result["error"] = result["stderr"]

            # Update progress during full scan
            if scan is not None and hasattr(scan, 'progress'):
                total_ports = 65535
                ports_scanned = len(scan_result.get("open_ports", [])) + len(scan_result.get("closed_ports", []))
                
                if total_ports > 0:
                    progress_per_port = (85 / total_ports) if total_ports > 0 else 1
                    calculated_progress = min(10 + int((ports_scanned / max(total_ports, 1)) * 85), 95)
                    scan.progress = calculated_progress

            return scan_result
        finally:
            await self._release_scan_lock()

    async def terminate_scan_process(self, scan_id: int):
        """
        Terminate a running scan process.

        Args:
            scan_id: ID of the scan to cancel
        """
        if scan_id in self._running_processes:
            task = self._running_processes[scan_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._running_processes[scan_id]
            logger.info("Scan process terminated", scan_id=scan_id)

    async def _execute_nmap(self, cmd: list) -> Dict:
        """
        Execute nmap command with proper process management.

        Args:
            cmd: Command and arguments as list

        Returns:
            Dict with stdout, stderr, returncode
        """
        try:
            result = await run_command(cmd, timeout=self.timeout)
            return result
        except asyncio.CancelledError:
            logger.warning("Nmap scan cancelled")
            raise
