# NetScope OS Fingerprinter

"""
Operating system fingerprinting using Nmap.
"""

from typing import Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class OSFingerprinter:
    """
    OS fingerprinting using Nmap's -O flag.
    """

    def __init__(self):
        self.logger = logger.bind(fingerprinter="os")

    async def fingerprint_os(self, ip_address: str) -> Dict:
        """
        Perform OS fingerprinting on a target.

        Args:
            ip_address: Target IP address

        Returns:
            OS fingerprinting results
        """
        self.logger.info("Fingerprinting OS", ip=ip_address)

        cmd = ["nmap", "-O", "-T4", ip_address]  # OS detection

        try:
            import asyncio

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

            if process.returncode == 0:
                return self._parse_os_output(stdout.decode(), ip_address)
            else:
                return {
                    "ip_address": ip_address,
                    "detected": False,
                    "error": stderr.decode(),
                }

        except Exception as e:
            self.logger.error("OS fingerprinting failed", error=str(e))
            return {"ip_address": ip_address,
                    "detected": False, "error": str(e)}

    def _parse_os_output(self, output: str, ip_address: str) -> Dict:
        """Parse Nmap OS fingerprinting output."""
        result = {
            "ip_address": ip_address,
            "detected": False,
            "os_name": None,
            "os_gen": None,
            "os_vendor": None,
            "accuracy": 0,
        }

        in_os_section = False

        for line in output.split("\n"):
            if "OS details:" in line or "Operating System:" in line:
                # Try to extract OS info from single-line output
                if "Linux" in line or "Windows" in line or "macOS" in line:
                    result["detected"] = True
                    result["os_name"] = self._extract_os(line)

            elif "Device type:" in line:
                # e.g., "Device type: general purpose"
                result["device_type"] = line.split(":")[1].strip()

            elif "Running:" in line:
                # e.g., "Running (JUST SOME IP): Linux 4.x"
                if len(line.split(":")) > 1:
                    result["detected"] = True
                    run_info = line.split(":", 1)[1].strip()
                    result["os_name"] = self._extract_os(run_info)

            elif "OS CPE:" in line:
                result["cpe"] = line.split(":", 1)[1].strip()

            elif "OS details:" in line:
                if ":" in line:
                    result["os_name"] = line.split(":", 1)[1].strip()

            elif "Network Distance:" in line:
                result["hops"] = int(line.split(":")[1].strip().split()[0])

            elif "Uptime" in line:
                # Extract uptime
                pass

        return result

    def _extract_os(self, line: str) -> Optional[str]:
        """Extract OS name from a line."""
        os_keywords = [
            "Linux",
            "Windows",
            "macOS",
            "Darwin",
            "FreeBSD",
            "OpenBSD",
            "NetBSD",
            "Solaris",
            "SunOS",
        ]

        for keyword in os_keywords:
            if keyword in line:
                return keyword

        return None

    async def detect_detailed_os(self, ip_address: str) -> Dict:
        """
        Perform detailed OS detection.

        Args:
            ip_address: Target IP

        Returns:
            Detailed OS detection results
        """
        self.logger.info("Detailed OS detection", ip=ip_address)

        cmd = ["nmap", "-O", "--osscan-guess", "--osscan-limit", ip_address]

        try:
            import asyncio

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)

            if process.returncode == 0:
                return self._parse_detailed_os(stdout.decode(), ip_address)

        except Exception as e:
            self.logger.error("Detailed OS detection failed", error=str(e))

        return {"ip_address": ip_address, "detected": False}

    def _parse_detailed_os(self, output: str, ip_address: str) -> Dict:
        """Parse detailed OS detection output."""
        result = {
            "ip_address": ip_address,
            "detected": False,
            "os_name": None,
            "os_gen": None,
            "accuracy": 0,
        }

        for line in output.split("\n"):
            if "Aggressive OS guesses:" in line or "No exact OS matches for" in line:
                if "Aggressive OS guesses:" in line:
                    result["detected"] = True

                    # Try to extract the guessed OS
                    if "Linux" in line:
                        result["os_name"] = self._extract_os(line)

            elif "OS details:" in line and ":" in line:
                result["os_name"] = line.split(":", 1)[1].strip()

            elif "Device type:" in line:
                result["device_type"] = line.split(":", 1)[1].strip()

        return result

    async def get_os_profile(self, ip_address: str) -> Dict:
        """
        Get complete OS profile.

        Args:
            ip_address: Target IP

        Returns:
            Complete OS profile
        """
        self.logger.info("Getting OS profile", ip=ip_address)

        # Run both fingerprinting methods
        basic_result = await self.fingerprint_os(ip_address)

        if not basic_result.get("detected"):
            detailed_result = await self.detect_detailed_os(ip_address)

            if detailed_result.get("detected"):
                basic_result.update(detailed_result)

        return basic_result

    async def fingerprint_multiple(self, ip_addresses: list) -> Dict:
        """
        Fingerprint OS on multiple hosts.

        Args:
            ip_addresses: List of IP addresses

        Returns:
            OS fingerprinting results for all hosts
        """
        self.logger.info(
            "Fingerprinting multiple hosts",
            count=len(ip_addresses))

        results = {"hosts": [], "total": len(ip_addresses), "detected": 0}

        for ip in ip_addresses:
            result = await self.fingerprint_os(ip)

            if result.get("detected"):
                results["detected"] += 1

            results["hosts"].append(result)

        return results
