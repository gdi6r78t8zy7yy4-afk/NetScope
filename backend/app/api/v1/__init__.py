# NetScope API v1 Package

"""
API version 1 endpoints.
"""

from app.api.v1 import networks, discovery, scans, assets, vulnerabilities
from fastapi import APIRouter, Depends
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1"])

# Import and include all route modules

# Include routers with authentication middleware for sensitive endpoints
router.include_router(networks.router)
router.include_router(discovery.router)

# Scans router - requires authentication for write operations
logger.info("Including scans router with authentication")
router.include_router(scans.router)

# Assets router - requires authentication for write operations
logger.info("Including assets router with authentication")
router.include_router(assets.router)

# Vulnerabilities router - requires authentication for write operations
logger.info("Including vulnerabilities router with authentication")
router.include_router(vulnerabilities.router)

# Intelligence router is included in routes.py
__all__ = ["router"]
