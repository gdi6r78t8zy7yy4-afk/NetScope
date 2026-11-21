# NetScope Cleanup Scheduler

"""
Scheduled cleanup for old/absent hosts.
Runs automatically to remove hosts that haven't been detected in multiple scans.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.asset import Asset

logger = structlog.get_logger(__name__)

# Default configuration
DEFAULT_MAX_ABSENT_DAYS = 3
DEFAULT_CLEANUP_INTERVAL_HOURS = 24  # Run daily


class CleanupScheduler:
    """
    Scheduled cleanup service for removing absent hosts.

    This scheduler runs periodically to identify and remove hosts
    that have been absent from scans for a configurable number of scans.
    """

    def __init__(
        self,
        max_absent_days: int = DEFAULT_MAX_ABSENT_DAYS,
        cleanup_interval_hours: int = DEFAULT_CLEANUP_INTERVAL_HOURS,
    ):
        """
        Initialize the cleanup scheduler.

        Args:
            max_absent_days: Number of consecutive absent scans before removal
            cleanup_interval_hours: How often to run the cleanup job
        """
        self.max_absent_days = max_absent_days
        self.cleanup_interval_hours = cleanup_interval_hours
        self._running = False
        self._last_run: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self.logger = logger.bind(scheduler="cleanup")

    async def run_cleanup(self, db: AsyncSession) -> dict:
        """
        Run the cleanup job to remove absent hosts.

        Args:
            db: Database session

        Returns:
            Cleanup results dictionary
        """
        try:
            # Find hosts that have been absent for max_absent_days consecutive
            # scans
            result = await db.execute(
                select(Asset).where(
                    Asset.consecutive_absent_count >= self.max_absent_days
                )
            )
            hosts_to_remove = list(result.scalars().all())

            removed_count = 0
            asset_ips_removed = []

            for host in hosts_to_remove:
                ip_address = host.ip_address
                # Remove the host and associated data
                await db.delete(host)
                removed_count += 1
                asset_ips_removed.append(ip_address)

                self.logger.info(
                    "Removed absent host during cleanup",
                    ip_address=ip_address,
                    consecutive_absent_count=host.consecutive_absent_count,
                )

            await db.commit()

            self._last_run = datetime.now()

            self.logger.info(
                "Cleanup completed",
                hosts_removed=removed_count,
                max_absent_days=self.max_absent_days,
            )

            return {
                "status": "success",
                "hosts_removed": removed_count,
                "max_absent_days": self.max_absent_days,
                "removed_host_ips": asset_ips_removed,
                "run_time": self._last_run.isoformat(),
            }

        except Exception as e:
            self.logger.error("Cleanup failed", error=str(e))
            raise

    async def run_cleanup_job(self) -> dict:
        """
        Run cleanup with automatic session management.

        Returns:
            Cleanup results dictionary
        """
        async for session in get_async_session():
            try:
                return await self.run_cleanup(session)
            finally:
                break  # Only run with first session

        return {"status": "error", "message": "Failed to get database session"}

    async def _cleanup_loop(self) -> None:
        """Background loop for running cleanup at intervals."""
        while self._running:
            try:
                await asyncio.sleep(
                    self.cleanup_interval_hours * 3600
                )  # Convert hours to seconds
                if self._running:
                    try:
                        await self.run_cleanup_job()
                    except Exception as e:
                        self.logger.error(
                            "Error running cleanup job", error=str(e))
            except asyncio.CancelledError:
                break

    def start(self) -> None:
        """Start the scheduled cleanup job."""
        if self._running:
            self.logger.warning("Cleanup scheduler already running")
            return

        self._running = True
        self.logger.info(
            "Cleanup scheduler started",
            interval_hours=self.cleanup_interval_hours,
            max_absent_days=self.max_absent_days,
        )

        # Run cleanup immediately once
        asyncio.create_task(self.run_cleanup_job())

        # Start the background loop
        self._task = asyncio.create_task(self._cleanup_loop())

    def stop(self) -> None:
        """Stop the scheduled cleanup job."""
        self._running = False
        if self._task:
            self._task.cancel()
            self.logger.info("Cleanup scheduler stopped")

    def get_status(self) -> dict:
        """Get current scheduler status."""
        return {
            "running": self._running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run_in_hours": self.cleanup_interval_hours if self._running else 0,
            "max_absent_days": self.max_absent_days,
        }


# Global scheduler instance
_cleanup_scheduler: Optional[CleanupScheduler] = None


def get_cleanup_scheduler() -> CleanupScheduler:
    """
    Get or create the global cleanup scheduler.

    Returns:
        CleanupScheduler instance
    """
    global _cleanup_scheduler

    if _cleanup_scheduler is None:
        _cleanup_scheduler = CleanupScheduler()

    return _cleanup_scheduler


async def cleanup_absent_hosts(
        max_absent_days: int = DEFAULT_MAX_ABSENT_DAYS) -> dict:
    """
    Standalone function to run cleanup without scheduler.

    Args:
        max_absent_days: Number of consecutive absent scans before removal

    Returns:
        Cleanup results dictionary
    """
    scheduler = CleanupScheduler(max_absent_days=max_absent_days)
    return await scheduler.run_cleanup_job()
