# NetScope Scan Worker

"""
Background worker for scan operations.
"""

import asyncio
from typing import Dict, List

import structlog

logger = structlog.get_logger(__name__)


class ScanWorker:
    """
    Background worker for executing scans.
    
    Handles scan execution, progress tracking,
    and result processing.
    """
    
    def __init__(self):
        self.logger = logger.bind(worker="scan")
        self.active_scans: Dict[int, asyncio.Task] = {}
    
    async def start_scan(
        self,
        scan_id: int,
        target: str,
        scan_type: str = "discovery"
    ):
        """
        Start a background scan.
        
        Args:
            scan_id: Scan ID
            target: Target to scan
            scan_type: Type of scan
            
        Returns:
            Scan task ID
        """
        self.logger.info(
            "Starting background scan",
            scan_id=scan_id,
            target=target
        )
        
        task = asyncio.create_task(
            self._execute_scan(scan_id, target, scan_type)
        )
        
        self.active_scans[scan_id] = task
        
        return task
    
    async def _execute_scan(
        self,
        scan_id: int,
        target: str,
        scan_type: str
    ):
        """
        Execute a scan in the background.
        
        Args:
            scan_id: Scan ID
            target: Target to scan
            scan_type: Type of scan
        """
        try:
            # Update progress
            await self._emit_progress(scan_id, 10, "starting")
            
            if scan_type == "discovery":
                result = await self._run_discovery_scan(target)
            elif scan_type == "port_scan":
                result = await self._run_port_scan(target)
            else:
                result = {"error": "Unknown scan type"}
            
            # Update progress
            await self._emit_progress(scan_id, 100, "completed")
            
            return result
            
        except Exception as e:
            self.logger.error("Scan failed", error=str(e))
            
            # Update progress
            await self._emit_progress(scan_id, 0, "failed")
            
            return {"error": str(e)}
    
    async def _run_discovery_scan(self, target: str) -> Dict:
        """Run a discovery scan."""
        from app.engines.discovery.active import ActiveDiscoveryEngine
        
        engine = ActiveDiscoveryEngine()
        
        return await engine.run_active_scan([target])
    
    async def _run_port_scan(self, target: str) -> Dict:
        """Run a port scan."""
        from app.engines.port_scanner.nmap_engine import NmapPortScanner
        
        scanner = NmapPortScanner()
        
        return await scanner.scan_common_ports(target)
    
    async def _emit_progress(
        self,
        scan_id: int,
        progress: int,
        status: str
    ):
        """Emit scan progress event."""
        from app.websocket.events import emit_scan_progress
        
        await emit_scan_progress(scan_id, progress, status)
    
    async def cancel_scan(self, scan_id: int) -> bool:
        """
        Cancel a running scan.
        
        Args:
            scan_id: Scan ID
            
        Returns:
            True if cancelled, False if not found
        """
        if scan_id in self.active_scans:
            task = self.active_scans[scan_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.active_scans[scan_id]
            
            await self._emit_progress(scan_id, 0, "cancelled")
            
            return True
        
        return False
    
    async def get_active_scans(self) -> Dict[int, asyncio.Task]:
        """Get all active scans."""
        return self.active_scans
