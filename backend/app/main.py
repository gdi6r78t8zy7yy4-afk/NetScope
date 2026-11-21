# NetScope Main Application

"""
FastAPI application entry point.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Callable, Awaitable

import structlog
from sqlalchemy import select, update, and_

from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import api_router
from app.core.config import settings
from app.models.scan import Scan
from app.database import get_async_session
from app.middleware.request_id import get_log_context


# Rate limiting storage (in-memory for single instance)
# For production, use Redis or similar distributed store
_rate_limit_store: dict[str, list[float]] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded_ip = request.headers.get("x-forwarded-for")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next) -> Response:
    """Rate limiting middleware using sliding window algorithm."""
    client_ip = get_client_ip(request)
    path = request.url.path

    if any(skip in path for skip in ["/health", "/docs", "/openapi.json"]):
        return await call_next(request)

    rate_limits = {
        "/api/v1/": (100, 60),
        "/api/v1/scans": (30, 60),
        "/api/v1/users": (50, 60),
        "/api/v1/assets": (60, 60),
    }

    limit, window = 100, 60
    for prefix, (limit_val, window_val) in rate_limits.items():
        if path.startswith(prefix):
            limit, window = limit_val, window_val
            break

    current_time = asyncio.get_event_loop().time()
    window_start = current_time - window

    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    _rate_limit_store[client_ip] = [
        timestamp
        for timestamp in _rate_limit_store[client_ip]
        if timestamp > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= limit:
        remaining = 0
        retry_after = int(
            window - (current_time - _rate_limit_store[client_ip][0]))

        return JSONResponse(
            status_code=429,
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(current_time + window)),
                "Retry-After": str(retry_after),
            },
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Please try again in {retry_after} seconds.",
                "limit": limit,
                "window": window,
            },
        )

    _rate_limit_store[client_ip].append(current_time)
    remaining = max(0, limit - len(_rate_limit_store[client_ip]))

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(current_time + window))

    return response


def get_cors_origins() -> list[str]:
    if settings.debug:
        return ["*"]

    origins = []
    if settings.allowed_origins:
        for origin in settings.allowed_origins.split(","):
            origin = origin.strip()
            if origin:
                origins.append(origin)

    if not origins:
        origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://localhost:3000",
        ]

    return origins


async def check_database() -> dict:
    try:
        from app.database import engine

        async with engine.begin() as conn:
            await conn.execute(asyncio.sleep(0))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


async def check_nvd_api() -> dict:
    try:
        from app.services.intelligence.nvd import NVDClient

        client = NVDClient()
        await client.fetch_cves()
        return {"status": "healthy", "api": "nvd"}
    except Exception as e:
        return {"status": "unhealthy", "api": "nvd", "error": str(e)}


async def check_cisa_api() -> dict:
    try:
        from app.services.intelligence.cisa import CISAClient

        client = CISAClient()
        await client.fetch_kev_catalog()
        return {"status": "healthy", "api": "cisa"}
    except Exception as e:
        return {"status": "unhealthy", "api": "cisa", "error": str(e)}


async def check_nmap() -> dict:
    try:
        import subprocess  # nosec B404, B603, B607

        result = subprocess.run(["nmap", "--version"], capture_output=True)  # nosec B404, B603, B607
        if result.returncode == 0:
            return {"status": "healthy", "tool": "nmap"}
        return {"status": "unhealthy",
                "tool": "nmap", "error": "not installed"}
    except Exception as e:
        return {"status": "unhealthy", "tool": "nmap", "error": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name} v{settings.app_version}")

    from app.database import engine, init_db

    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database: {e}")

    # Start the scan queue processor
    try:
        from app.services.scan_scheduler import processor

        await processor.start()
        print("Scan queue processor started")
    except Exception as e:
        print(f"Failed to start scan queue processor: {e}")

    # Start the intelligence sync worker
    try:
        from app.workers.intelligence_sync import IntelligenceSyncWorker

        intelligence_worker = IntelligenceSyncWorker(
            update_interval=86400)  # 24 hours
        await intelligence_worker.start()
        print("Intelligence sync worker started")

        # Trigger initial sync on startup if database is empty
        from app.engines.vulnerability.intelligence import (
            IntelligenceSync as IntelSyncEngine,
        )

        # Get database session and check vulnerability count
        from sqlalchemy import select, func
        from app.models.vulnerability import Vulnerability

        async with get_async_session() as db:
            vuln_result = await db.execute(select(func.count(Vulnerability.id)))
            vuln_count = vuln_result.scalar_one()

        if vuln_count == 0:
            print("No vulnerabilities found in database. Triggering initial sync...")
            try:
                async with get_async_session() as db:
                    engine = IntelSyncEngine()
                    result = await engine.sync_to_database(db)
                    print(f"Initial intelligence sync completed: {result}")
            except Exception as e:
                print(f"Initial sync failed (will retry in background): {e}")
        else:
            print(
                f"Found {vuln_count} vulnerabilities in database. Skipping initial sync."
            )
    except Exception as e:
        print(f"Failed to start intelligence sync worker: {e}")

    # Find scans that have been "running" for more than 5 minutes (startup recovery)
    timeout_delta = timedelta(minutes=5)
    cutoff_time = datetime.now() - timeout_delta

    try:
        async with get_async_session() as db:
            result = await db.execute(
                select(Scan).where(
                    Scan.status == "running",
                    Scan.started_at < cutoff_time
                )
            )
            hung_scans = result.scalars().all()
            
            if hung_scans:
                print(f"Found {len(hung_scans)} hung scans from previous session")
                
                for scan in hung_scans:
                    # Mark as failed with appropriate message
                    stmt = (
                        update(Scan)
                        .where(Scan.id == scan.id)
                        .values(
                            status="failed",
                            completed_at=datetime.now(),
                            notes=f"Recovered from hung state (started at {scan.started_at.isoformat()})"
                        )
                    )
                    await db.execute(stmt)
                    await db.commit()
                    
                    print(f"  - Recovered scan {scan.id}: marked as failed")
                
                print(f"Recovered {len(hung_scans)} hung scans on startup")

    except Exception as e:
        print(f"Failed to recover hung scans: {e}")

    # NEW: Start periodic hung scan recovery task
    async def hung_scan_recovery_task():
        """Periodically check for and mark hung scans as failed."""
        from datetime import timedelta
        from sqlalchemy import or_
        
        timeout_seconds = getattr(settings, 'scan_timeout_seconds', 3600)
        recovery_interval = getattr(settings, 'scan_health_check_interval_seconds', 60)
        
        while True:
            try:
                await asyncio.sleep(recovery_interval)  # Check every minute
                
                async with get_async_session() as db:
                    result = await db.execute(
                        select(Scan).where(
                            Scan.status == "running",
                            or_(
                                Scan.started_at < (datetime.now() - timedelta(seconds=timeout_seconds)),
                                and_(
                                    Scan.started_at == None,
                                    Scan.created_at < (datetime.now() - timedelta(minutes=10))
                                )
                            )
                        )
                    )
                    hung_scans = result.scalars().all()
                    
                    for scan in hung_scans:
                        stmt = (
                            update(Scan)
                            .where(Scan.id == scan.id)
                            .values(
                                status="failed",
                                completed_at=datetime.now(),
                                notes=f"Marked as failed by hung scan recovery"
                            )
                        )
                        await db.execute(stmt)
                        await db.commit()
                        
                        logger = structlog.get_logger(__name__)
                        logger.warning(
                            "Hung scan recovered by cleanup task",
                            scan_id=scan.id
                        )
                        
            except Exception as e:
                logger = structlog.get_logger(__name__)
                logger.error("Hung scan recovery failed", error=str(e))

    # Start the background task
    asyncio.create_task(hung_scan_recovery_task())

    yield

    # Stop the scan queue processor
    try:
        from app.services.scan_scheduler import processor

        await processor.stop()
        print("Scan queue processor stopped")
    except Exception as e:
        print(f"Failed to stop scan queue processor: {e}")

    # Stop the intelligence sync worker
    try:
        from app.workers.intelligence_sync import IntelligenceSyncWorker

        intelligence_worker = IntelligenceSyncWorker(update_interval=86400)
        await intelligence_worker.stop()
        print("Intelligence sync worker stopped")
    except Exception as e:
        print(f"Failed to stop intelligence sync worker: {e}")

    # Stop the database engine
    try:
        from app.database import get_sync_engine

        sync_engine = get_sync_engine()
        sync_engine.dispose()
        print("Database engine disposed")
    except Exception as e:
        print(f"Failed to dispose database engine: {e}")

    print("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    description="Network Discovery & Vulnerability Intelligence Platform",
    version=settings.app_version,
    lifespan=lifespan,
)

app.middleware("http")(rate_limit_middleware)

cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/extended")
async def extended_health_check():
    results = await asyncio.gather(
        check_database(), check_nvd_api(), check_cisa_api(), check_nmap()
    )

    statuses = [r["status"] for r in results]

    if "unhealthy" in statuses:
        overall_status = "degraded"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    detailed_status = {}
    for result in results:
        api_name = result.get("api") or result.get("tool") or "database"
        detailed_status[api_name] = {
            "status": result["status"],
            **{k: v for k, v in result.items() if k != "status"},
        }

    return {
        "overall_status": overall_status,
        "timestamp": asyncio.get_event_loop().time(),
        "services": detailed_status,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    log_context = get_log_context(request)
    print(f"[{request_id}] Exception occurred: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "message": "An internal error occurred",
            "request_id": request_id,
        },
    )


# Include routers
app.include_router(api_router)


# Add health check endpoint at /api/v1/health (must be after api_router
# include)
@app.get("/api/v1/health")
async def health_check_v1():
    """Health check endpoint for API v1."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
