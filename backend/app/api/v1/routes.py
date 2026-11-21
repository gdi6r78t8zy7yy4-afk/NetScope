# NetScope API Routes

"""
Main API routes file that registers all endpoints.
"""

from app.api.v1.intelligence import router as intelligence_router
from fastapi import APIRouter

from app.api.v1 import router as v1_router


# Main API router - provides v1 endpoints at /api/v1/
api_router = APIRouter()

# Include all versioned routers first
api_router.include_router(v1_router)

# Include intelligence router

api_router.include_router(intelligence_router)


# Root endpoint (serves at /)
@api_router.get("/")
async def root():
    """Root endpoint."""
    return {"name": "NetScope API", "version": "1.0.0", "status": "running"}


# Health check endpoint at /health (after v1_router to ensure it's registered)
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@api_router.get("/api-info")
async def api_info():
    """API information endpoint."""
    return {
        "version": "1.0.0",
        "routes": [
            "/api/v1/networks",
            "/api/v1/discovery",
            "/api/v1/scans",
            "/api/v1/assets",
            "/api/v1/vulnerabilities",
        ],
    }
