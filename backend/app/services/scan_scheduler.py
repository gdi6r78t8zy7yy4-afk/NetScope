# NetScope Scan Scheduler Service

"""
Background worker for processing scan queue with concurrent scan limits.
"""

import asyncio
from datetime import datetime
from typing import Optional
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_async_session
from app.models.scan import Scan
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


class ScanQueueProcessor:
    """
    Background processor that manages a queue of pending scans.

    When scans are created, they're added to the queue. The processor
    runs scans when capacity becomes available (running < max_concurrent_scans).

    Features:
    - Enforces max_concurrent_scans limit
    - Processes scans in FIFO order
    - Handles failures gracefully
    - Works alongside the run_scan endpoint
    """

    def __init__(self):
        self.max_concurrent_scans = settings.max_concurrent_scans
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scan queue processor."""
        if self._running:
            logger.warning("Scan queue processor already running")
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue_loop())
        logger.info(
            "Scan queue processor started",
            max_concurrent_scans=self.max_concurrent_scans,
        )

    async def stop(self) -> None:
        """Stop the scan queue processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Scan queue processor stopped")

    async def _process_queue_loop(self) -> None:
        """Main loop that processes pending scans when capacity is available."""
        while self._running:
            try:
                await self._try_start_pending_scan()
                # Wait before next check to avoid tight loop
                await asyncio.sleep(1)
            except Exception as e:
                logger.error("Error in scan queue processor", error=str(e))
                await asyncio.sleep(5)  # Backoff on error

    async def _try_start_pending_scan(self) -> bool:
        """
        Try to start a pending scan if capacity is available.

        Returns:
            bool: True if a scan was started, False otherwise
        """
        try:
            # Get current running scans count
            async for session in get_async_session():
                try:
                    # Count running scans
                    running_result = await session.execute(
                        select(Scan).where(Scan.status == "running")
                    )
                    running_scans = list(running_result.scalars().all())

                    # Count pending scans
                    pending_result = await session.execute(
                        select(Scan).where(Scan.status == "pending")
                    )
                    pending_scans = list(pending_result.scalars().all())

                    # Check if we have capacity
                    has_capacity = len(
                        running_scans) < self.max_concurrent_scans

                    if has_capacity and pending_scans:
                        # Get the oldest pending scan
                        next_scan = pending_scans[0]

                        logger.info(
                            "Starting queued scan",
                            scan_id=next_scan.id,
                            scan_name=next_scan.name or "Unnamed",
                            pending_count=len(pending_scans) - 1,
                            running_count=len(running_scans),
                        )

                        # Mark scan as running
                        stmt = (
                            update(Scan)
                            .where(Scan.id == next_scan.id)
                            .values(status="running", started_at=datetime.now())
                        )
                        await session.execute(stmt)
                        await session.commit()

                        # Execute the scan in background
                        asyncio.create_task(
                            self._execute_scan(
                                next_scan, session))

                        return True

                    elif has_capacity:
                        logger.debug("No pending scans to process")
                    else:
                        logger.debug(
                            "Max concurrent scans reached",
                            running_count=len(running_scans),
                            max_concurrent=self.max_concurrent_scans,
                        )

                    break  # Only process one scan per iteration

                except Exception as e:
                    logger.error(
                        "Error trying to start pending scan",
                        error=str(e))

        except Exception as e:
            logger.error(
                "Error getting session in scan queue processor",
                error=str(e))

        return False

    async def _execute_scan(self, scan: Scan, session: AsyncSession) -> None:
        """Execute a single scan and update its status."""
        from app.engines.port_scanner.nmap_engine import NmapPortScanner
        from app.engines.discovery.active import ActiveDiscoveryEngine
        from app.core.authorization_service import get_authorization_service

        scanner = NmapPortScanner()

        # Validate target
        auth_service = get_authorization_service()
        validation_result = auth_service.validate_target(scan.target_cidr)

        if not validation_result.get("valid"):
            logger.warning(
                "Scan target not authorized",
                scan_id=scan.id,
                target=scan.target_cidr,
            )

            stmt = (
                update(Scan)
                .where(Scan.id == scan.id)
                .values(status="failed", completed_at=datetime.now())
            )
            await session.execute(stmt)
            await session.commit()
            return

        try:
            if scan.scan_type == "discovery":
                discovery_engine = ActiveDiscoveryEngine(
                    max_concurrent_hosts=5, scan_timeout=settings.scan_timeout_seconds
                )

                result_data = await discovery_engine.discover_with_nmap(
                    scan.target_cidr, rate_limit=getattr(
                        scan, "rate_limit", "medium")
                )

                # Parse and save discovery results
                discovered_hosts = result_data.get("hosts", [])
                scan.hosts_found = len(discovered_hosts)

                # Save assets
                if discovered_hosts:
                    from app.models.asset import Asset

                    for host in discovered_hosts:
                        ip = (
                            host.get("ip_address")
                            or host.get("ip")
                            or host.get("ipaddress")
                        )
                        if not ip:
                            continue

                        # Check if asset already exists
                        existing_result = await session.execute(
                            select(Asset).where(Asset.ip_address == ip)
                        )
                        existing_asset = existing_result.scalars().first()

                        if not existing_asset:
                            new_asset = Asset(
                                ip_address=ip,
                                mac_address=host.get(
                                    "mac_address") or host.get("mac"),
                                hostname=host.get("hostname", ""),
                                device_type=host.get("device_type")
                                or host.get("device"),
                                operating_system=host.get("operating_system")
                                or host.get("os"),
                                confidence_level=host.get("confidence")
                                or host.get("confidence_level")
                                or "low",
                            )
                            session.add(new_asset)

                await session.commit()

            elif scan.scan_type in ["common", "port_range", "full_tcp", "single_port"]:
                # Port scan
                result_data = await scanner.scan_ports(
                    scan.target_cidr, getattr(scan, "ports", None) or []
                )
                scan.hosts_found = result_data.get("hosts_found", 0)

            # Update scan status to completed
            scan.status = "completed"
            scan.completed_at = datetime.now()
            await session.commit()

            logger.info(
                "Scan completed successfully",
                scan_id=scan.id,
                hosts_found=scan.hosts_found,
            )

        except asyncio.TimeoutError:
            scan.status = "failed"
            scan.completed_at = datetime.now()
            await session.commit()
            logger.warning("Scan timed out", scan_id=scan.id)

        except Exception as e:
            scan.status = "failed"
            scan.completed_at = datetime.now()
            await session.commit()
            logger.error(
                "Scan failed with error",
                scan_id=scan.id,
                error=str(e))

    def get_queue_stats(self) -> dict:
        """Get current queue statistics."""
        return {
            "max_concurrent_scans": self.max_concurrent_scans,
            "running": getattr(self, "_stats_running", 0),
            "pending": getattr(self, "_stats_pending", 0),
        }


# Global processor instance
processor = ScanQueueProcessor()
