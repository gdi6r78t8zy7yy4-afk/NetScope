# NetScope Scan Scheduler Service

"""
Background worker for processing scan queue with concurrent scan limits.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_async_session, AsyncSessionLocal
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
                # Add timeouts to prevent the entire processor from hanging
                try:
                    await asyncio.wait_for(
                        self._try_start_pending_scan(), 
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("_try_start_pending_scan() timed out")
                
                try:
                    await asyncio.wait_for(
                        self._check_pending_timeouts(),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("_check_pending_timeouts() timed out")
                    
                try:
                    await asyncio.wait_for(
                        self._check_running_timeouts(), 
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("_check_running_timeouts() timed out")
                    
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
        session = AsyncSessionLocal()
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

                # Refresh the scan object to ensure it's not expired
                await session.refresh(next_scan)

                # Execute the scan in background (no session needed - creates its own)
                asyncio.create_task(
                    self._execute_scan(next_scan))

                return True

            elif has_capacity:
                logger.debug("No pending scans to process")
            else:
                logger.debug(
                    "Max concurrent scans reached",
                    running_count=len(running_scans),
                    max_concurrent=self.max_concurrent_scans,
                )

        except Exception as e:
            logger.error(
                "Error in scan queue processor", error=str(e))
        finally:
            await session.close()

        return False

    async def _execute_scan(self, scan: Scan) -> None:
        """Execute a single scan and update its status."""
        from app.engines.port_scanner.nmap_engine import NmapPortScanner
        from app.engines.discovery.active import ActiveDiscoveryEngine
        from app.core.authorization_service import get_authorization_service

        # Create a new session for scan execution
        session = AsyncSessionLocal()
        try:
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
                    await session.commit()

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

        finally:
            await session.close()

    async def _execute_scan(self, scan: Scan) -> None:
        """Execute a single scan and update its status."""
        from app.engines.port_scanner.nmap_engine import NmapPortScanner
        from app.engines.discovery.active import ActiveDiscoveryEngine
        from app.core.authorization_service import get_authorization_service

        # Create a new session for scan execution
        session = AsyncSessionLocal()
        try:
            scanner = NmapPortScanner()

            # Fetch the scan in this session to ensure we have fresh data
            result = await session.execute(select(Scan).where(Scan.id == scan.id))
            active_scan = result.scalar_one_or_none()
            if not active_scan:
                logger.error("Scan not found during execution", scan_id=scan.id)
                return

            # Validate target
            auth_service = get_authorization_service()
            validation_result = auth_service.validate_target(active_scan.target_cidr)

            if not validation_result.get("valid"):
                logger.warning(
                    "Scan target not authorized",
                    scan_id=active_scan.id,
                    target=active_scan.target_cidr,
                )

                stmt = (
                    update(Scan)
                    .where(Scan.id == active_scan.id)
                    .values(status="failed", completed_at=datetime.now())
                )
                await session.execute(stmt)
                await session.commit()
                return

            try:
                if active_scan.scan_type == "discovery":
                    discovery_engine = ActiveDiscoveryEngine(
                        max_concurrent_hosts=5, scan_timeout=settings.scan_timeout_seconds
                    )

                    result_data = await discovery_engine.discover_with_nmap(
                        active_scan.target_cidr, rate_limit=getattr(
                            active_scan, "rate_limit", "medium")
                    )

                    # Parse and save discovery results
                    discovered_hosts = result_data.get("hosts", [])
                    active_scan.hosts_found = len(discovered_hosts)

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

                elif active_scan.scan_type in ["common", "port_range", "full_tcp", "single_port"]:
                    # Port scan
                    result_data = await scanner.scan_ports(
                        active_scan.target_cidr, getattr(active_scan, "ports", None) or []
                    )
                    active_scan.hosts_found = result_data.get("hosts_found", 0)
                    await session.commit()

                # Update scan status to completed
                active_scan.status = "completed"
                active_scan.completed_at = datetime.now()
                await session.commit()

                logger.info(
                    "Scan completed successfully",
                    scan_id=active_scan.id,
                    hosts_found=active_scan.hosts_found,
                )

            except asyncio.TimeoutError:
                active_scan.status = "failed"
                active_scan.completed_at = datetime.now()
                await session.commit()
                logger.warning("Scan timed out", scan_id=active_scan.id)

            except Exception as e:
                active_scan.status = "failed"
                active_scan.completed_at = datetime.now()
                await session.commit()
                logger.error(
                    "Scan failed with error",
                    scan_id=active_scan.id,
                    error=str(e))

        finally:
            await session.close()

    async def _check_running_timeouts(self) -> None:
        """Check for running scans that have exceeded their timeout."""
        session = AsyncSessionLocal()
        try:
            # Get all running scans
            result = await session.execute(
                select(Scan).where(Scan.status == "running")
            )
            running_scans = list(result.scalars().all())
            
            # Use the global timeout setting (default 3600 seconds)
            timeout_seconds = getattr(settings, 'scan_timeout_seconds', 3600)
            
            for scan in running_scans:
                # Calculate elapsed time since started_at
                if scan.started_at:
                    elapsed = datetime.now() - scan.started_at
                    timeout_delta = timedelta(seconds=timeout_seconds)
                    
                    if elapsed > timeout_delta:
                        # Mark scan as failed due to timeout
                        stmt = (
                            update(Scan)
                            .where(Scan.id == scan.id)
                            .values(
                                status="failed",
                                completed_at=datetime.now()
                            )
                        )
                        await session.execute(stmt)
                        await session.commit()
                        
                        logger.warning(
                            "Running scan timed out",
                            scan_id=scan.id,
                            elapsed_seconds=int(elapsed.total_seconds()),
                            timeout_seconds=timeout_seconds,
                        )
                
        except Exception as e:
            logger.error(
                "Error checking running scan timeouts",
                error=str(e))
        
        finally:
            await session.close()

    async def _check_pending_timeouts(self) -> None:
        """Check for pending scans that have been waiting too long and fail them."""
        session = AsyncSessionLocal()
        try:
            # Get pending scans
            result = await session.execute(
                select(Scan).where(Scan.status == "pending")
            )
            pending_scans = list(result.scalars().all())
            
            for scan in pending_scans:
                # Calculate time since creation
                if scan.created_at:
                    age = datetime.now() - scan.created_at
                    # Timeout after 5 minutes (300 seconds) in pending state
                    timeout = timedelta(seconds=settings.scan_timeout_seconds if hasattr(settings, 'scan_timeout_seconds') else 300)
                    
                    if age > timeout:
                        # Fail the scan
                        stmt = (
                            update(Scan)
                            .where(Scan.id == scan.id)
                            .values(
                                status="failed",
                                completed_at=datetime.now()
                            )
                        )
                        await session.execute(stmt)
                        await session.commit()
                        logger.warning(
                            "Pending scan timed out",
                            scan_id=scan.id,
                            wait_time_seconds=int(age.total_seconds()),
                        )
        
        except Exception as e:
            logger.error(
                "Error checking pending timeouts",
                error=str(e))
        
        finally:
            await session.close()

    def get_queue_stats(self) -> dict:
        """Get current queue statistics."""
        return {
            "max_concurrent_scans": self.max_concurrent_scans,
            "running": getattr(self, "_stats_running", 0),
            "pending": getattr(self, "_stats_pending", 0),
        }


# Global processor instance
processor = ScanQueueProcessor()
