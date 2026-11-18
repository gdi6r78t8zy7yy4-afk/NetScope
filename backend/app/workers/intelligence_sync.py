# NetScope Intelligence Sync Worker

"""
Background worker for intelligence synchronization.
"""

import asyncio
from typing import Dict

import structlog

logger = structlog.get_logger(__name__)


class IntelligenceSyncWorker:
    """
    Background worker for intelligence synchronization.
    
    Periodically syncs vulnerability databases
    from external sources.
    """
    
    def __init__(self, update_interval: int = 86400):
        """
        Initialize the worker.
        
        Args:
            update_interval: Update interval in seconds (default: 24h)
        """
        self.update_interval = update_interval
        self.logger = logger.bind(worker="intelligence_sync")
        self.running = False
        self.sync_task = None
    
    async def start(self):
        """Start the synchronization worker."""
        self.running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        self.logger.info("Intelligence sync worker started")
    
    async def stop(self):
        """Stop the synchronization worker."""
        self.running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Intelligence sync worker stopped")
    
    async def _sync_loop(self):
        """Main synchronization loop."""
        from app.engines.vulnerability.intelligence import IntelligenceSync
        
        engine = IntelligenceSync()
        
        while self.running:
            try:
                # Perform sync
                result = await engine.sync_all()
                
                self.logger.info(
                    "Intelligence sync completed",
                    results=result
                )
                
                # Emit completion event
                from app.websocket.events import emit_intelligence_synced
                
                for synced in result.get("synced", []):
                    await emit_intelligence_synced(
                        synced["source"],
                        "success"
                    )
                
                for failed in result.get("failed", []):
                    await emit_intelligence_synced(
                        failed["source"],
                        "failed"
                    )
                
                # Wait for next sync
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(
                    "Intelligence sync failed",
                    error=str(e)
                )
                
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def sync_now(self) -> Dict:
        """
        Perform an immediate synchronization.
        
        Returns:
            Sync results
        """
        from app.engines.vulnerability.intelligence import IntelligenceSync
        
        engine = IntelligenceSync()
        
        return await engine.sync_all()
