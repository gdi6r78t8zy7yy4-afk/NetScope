# NetScope Scan Manager

"""
Centralized scan management with process control and progress tracking.
"""

import asyncio
import subprocess
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from app.database import get_async_session
from app.models.scan import Scan, ScanTarget


class ScanStatus(str, Enum):
    """Scan status enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScanProcess:
    """Represents a running scan process."""

    scan_id: int
    process: subprocess.Popen
    task: asyncio.Task
    progress: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    cancelled: bool = False


class ScanManager:
    """
    Centralized scan manager with process control.

    This class manages all scanning operations, including:
    - Scan lifecycle (create, start, monitor, cancel)
    - Process control (spawn, terminate, timeout)
    - Progress tracking
    - Concurrency management
    """

    def __init__(self, max_concurrent_scans: int = 3):
        """
        Initialize scan manager.

        Args:
            max_concurrent_scans: Maximum number of simultaneous scans
        """
        self.max_concurrent_scans = max_concurrent_scans
        self.active_scans: Dict[int, ScanProcess] = {}
        self.queued_scans: List[Scan] = []
        self.running_count = 0
        self._lock = asyncio.Lock()
        self._scan_results: Dict[int, dict] = {}

    async def create_scan(
        self,
        name: Optional[str],
        scan_type: str,
        target_cidr: str,
        rate_limit: str = "medium",
        ports: Optional[str] = None,
    ) -> Scan:
        """
        Create a new scan record.

        Args:
            name: Optional scan name
            scan_type: Type of scan (discovery, port_scan, vulnerability)
            target_cidr: Target network CIDR
            rate_limit: Scan rate limit (low, medium, high)
            ports: Optional port list

        Returns:
            Created Scan model
        """
        scan = Scan(
            name=name,
            scan_type=scan_type,
            target_cidr=target_cidr,
            rate_limit=rate_limit,
            ports=ports,
        )

        async with get_async_session() as session:
            session.add(scan)
            await session.commit()
            await session.refresh(scan)

        return scan

    async def start_scan(self, scan_id: int) -> bool:
        """
        Start a pending scan.

        Args:
            scan_id: ID of scan to start

        Returns:
            True if started successfully, False otherwise
        """
        async with self._lock:
            # Check if scan is already running
            if scan_id in self.active_scans:
                return False

            # Check if we're at capacity
            if self.running_count >= self.max_concurrent_scans:
                # Add to queue
                async with get_async_session() as session:
                    scan = await session.get(Scan, scan_id)
                    if scan and scan.status == "pending":
                        self.queued_scans.append(scan)
                    return False

            # Start the scan
            result = await self._execute_scan(scan_id)
            return result

    async def _execute_scan(self, scan_id: int) -> bool:
        """
        Execute a scan process.

        Args:
            scan_id: ID of scan to execute

        Returns:
            True if scan completed successfully
        """
        async with get_async_session() as session:
            scan = await session.get(Scan, scan_id)
            if not scan or scan.status != "pending":
                return False

            # Update status
            scan.status = "running"
            scan.started_at = datetime.now()
            session.add(scan)
            await session.commit()

        self.running_count += 1

        try:
            # Create subprocess for scan
            cmd = [
                "nmap",
                "-sn",  # Ping scan
                "-T4",  # Aggressive timing
                scan.target_cidr,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Create progress tracking task
            async def track_progress():
                try:
                    stdout, stderr = await process.communicate()

                    # Parse output for progress
                    if process.returncode == 0:
                        lines = stdout.decode().split("\n")
                        # Estimate progress based on output
                        progress = min(100, len(lines))

                        async with get_async_session() as session:
                            scan = await session.get(Scan, scan_id)
                            if scan:
                                scan.progress = progress
                                scan.status = "completed"
                                scan.completed_at = datetime.now()
                                session.add(scan)
                                await session.commit()
                    else:
                        # Scan failed
                        error_msg = stderr.decode() if stderr else "Unknown error"

                        async with get_async_session() as session:
                            scan = await session.get(Scan, scan_id)
                            if scan:
                                scan.status = "failed"
                                scan.completed_at = datetime.now()
                                session.add(scan)
                                await session.commit()
                finally:
                    self.running_count -= 1
                    self.active_scans.pop(scan_id, None)

                    # Start queued scan if any
                    if (
                        self.queued_scans
                        and self.running_count < self.max_concurrent_scans
                    ):
                        queued_scan = self.queued_scans.pop(0)
                        await self._execute_scan(queued_scan.id)

            task = asyncio.create_task(track_progress())

            async with self._lock:
                self.active_scans[scan_id] = ScanProcess(
                    scan_id=scan_id, process=process, task=task
                )

            return True

        except Exception as e:
            # Update scan status to failed
            async with get_async_session() as session:
                scan = await session.get(Scan, scan_id)
                if scan:
                    scan.status = "failed"
                    scan.completed_at = datetime.now()
                    session.add(scan)
                    await session.commit()

            self.running_count -= 1
            return False

    async def cancel_scan(self, scan_id: int) -> bool:
        """
        Cancel a running scan.

        Args:
            scan_id: ID of scan to cancel

        Returns:
            True if cancelled successfully
        """
        async with self._lock:
            if scan_id not in self.active_scans:
                return False

            scan_process = self.active_scans[scan_id]

            # Cancel the task
            scan_process.cancelled = True
            scan_process.task.cancel()

            # Terminate the process
            try:
                if hasattr(scan_process, "process"):
                    scan_process.process.terminate()
                    try:
                        await asyncio.wait_for(scan_process.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Force kill if termination fails
                        try:
                            scan_process.process.kill()
                        except ProcessLookupError:
                            pass
            except Exception:
                pass

            # Update database status
            async with get_async_session() as session:
                scan = await session.get(Scan, scan_id)
                if scan:
                    scan.status = "cancelled"
                    scan.completed_at = datetime.now()
                    session.add(scan)
                    await session.commit()

            self.running_count -= 1
            del self.active_scans[scan_id]

            # Start queued scan if any
            if self.queued_scans and self.running_count < self.max_concurrent_scans:
                queued_scan = self.queued_scans.pop(0)
                await self._execute_scan(queued_scan.id)

            return True

    async def get_scan(self, scan_id: int) -> Optional[Scan]:
        """
        Get scan by ID.

        Args:
            scan_id: ID of scan to retrieve

        Returns:
            Scan model or None if not found
        """
        async with get_async_session() as session:
            return await session.get(Scan, scan_id)

    async def list_scans(
        self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None
    ) -> List[Scan]:
        """
        List scans with optional filtering.

        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            status_filter: Filter by scan status

        Returns:
            List of Scan models
        """
        async with get_async_session() as session:
            from sqlalchemy import select

            query = select(Scan).order_by(Scan.created_at.desc())

            if status_filter:
                query = query.where(Scan.status == status_filter)

            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_scan_progress(self, scan_id: int) -> Optional[int]:
        """
        Get current progress of a running scan.

        Args:
            scan_id: ID of scan

        Returns:
            Progress percentage (0-100) or None if not found
        """
        async with self._lock:
            if scan_id in self.active_scans:
                return self.active_scans[scan_id].progress

        # Check database
        async with get_async_session() as session:
            scan = await session.get(Scan, scan_id)
            if scan:
                return scan.progress

        return None

    async def get_scan_results(self, scan_id: int) -> Optional[dict]:
        """
        Get scan results.

        Args:
            scan_id: ID of scan

        Returns:
            Scan results dict or None if not found
        """
        return self._scan_results.get(scan_id)

    def get_active_scan_count(self) -> int:
        """Get number of active scans."""
        return self.running_count

    def get_queued_scan_count(self) -> int:
        """Get number of queued scans."""
        return len(self.queued_scans)
