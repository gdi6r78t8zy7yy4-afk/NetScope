# NetScope WebSocket Events

"""
WebSocket event utilities.
"""

from app.websocket.manager import manager


async def emit_scan_progress(
        scan_id: int, progress: int, status: str = "running"):
    """
    Emit a scan progress event.

    Args:
        scan_id: Scan ID
        progress: Progress percentage (0-100)
        status: Scan status
    """
    await manager.broadcast_scan_progress(scan_id, progress, status)


async def emit_new_asset(asset: dict):
    """
    Emit a new asset discovery event.

    Args:
        asset: Asset information
    """
    await manager.broadcast_discovery_event("new_asset", asset)


async def emit_scan_complete(scan_id: int, results: dict):
    """
    Emit a scan completion event.

    Args:
        scan_id: Scan ID
        results: Scan results
    """
    await manager.broadcast_scan_progress(scan_id, 100, "completed")

    await manager.broadcast_discovery_event(
        "scan_complete", {"scan_id": scan_id, **results}
    )


async def emit_vulnerability_finding(finding: dict):
    """
    Emit a vulnerability finding event.

    Args:
        finding: Vulnerability finding
    """
    await manager.broadcast_vulnerability_finding(finding)


async def emit_intelligence_synced(source: str, status: str):
    """
    Emit an intelligence sync event.

    Args:
        source: Intelligence source
        status: Sync status
    """
    await manager.broadcast_intelligence_synced(source, status)
