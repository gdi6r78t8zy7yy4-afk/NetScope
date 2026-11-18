# NetScope Main Application

"""
FastAPI application entry point.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Callable, Awaitable

from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import api_router
from app.core.config import settings
from app.middleware.request_id import get_log_context


# Rate limiting storage (in-memory for single instance)
# For production, use Redis or similar distributed store
_rate_limit_store: dict[str, list[float]] = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded IP first
    forwarded_ip = request.headers.get("x-forwarded-for")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    # Fall back to client host
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Rate limiting middleware using sliding window algorithm.
    
    Configurable limits per endpoint based on path patterns.
    """
    client_ip = get_client_ip(request)
    path = request.url.path
    
    # Skip rate limiting for health checks and docs
    if any(skip in path for skip in ["/health", "/docs", "/openapi.json"]):
        return await call_next(request)
    
    # Rate limit configuration
    rate_limits = {
        "/api/v1/": (100, 60),      # 100 requests per 60 seconds
        "/api/v1/scans": (30, 60),   # Scanning endpoints have stricter limits
        "/api/v1/users": (50, 60),   # User endpoints
        "/api/v1/assets": (60, 60),  # Asset endpoints
    }
    
    # Determine rate limit for this endpoint
    limit, window = 100, 60  # Default: 100 req/60s
    for prefix, (limit_val, window_val) in rate_limits.items():
        if path.startswith(prefix):
            limit, window = limit_val, window_val
            break
    
    # Get current timestamp and client's request history
    current_time = asyncio.get_event_loop().time()
    window_start = current_time - window
    
    # Initialize or get client's request history
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    
    # Filter out old requests outside the window
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store[client_ip]
        if timestamp > window_start
    ]
    
    # Check if rate limit exceeded
    if len(_rate_limit_store[client_ip]) >= limit:
        remaining = 0
        retry_after = int(window - (current_time - _rate_limit_store[client_ip][0]))
        
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
            }
        )
    
    # Record this request
    _rate_limit_store[client_ip].append(current_time)
    remaining = max(0, limit - len(_rate_limit_store[client_ip]))
    
    # Build response with rate limit headers
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(current_time + window))
    
    return response


# Configure CORS with secure defaults
def get_cors_origins() -> list[str]:
    """Get allowed CORS origins from settings or environment."""
    if settings.debug:
        # In development, allow all origins
        return ["*"]
    
    # In production, use configured allowed origins
    origins = []
    if settings.allowed_origins:
        # Parse comma-separated origins
        for origin in settings.allowed_origins.split(","):
            origin = origin.strip()
            if origin:
                origins.append(origin)
    
    # Default to localhost for development
    if not origins:
        origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://localhost:3000",
        ]
    
    return origins


async def check_database() -> dict:
    """
    Check database connection status.
    
    Returns:
        dict: Database connection status
    """
    try:
        from app.database import engine
        async with engine.begin() as conn:
            await conn.execute(asyncio.sleep(0))  # Simple connectivity test
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


async def check_nvd_api() -> dict:
    """
    Check NVD API availability.
    
    Returns:
        dict: NVD API status
    """
    try:
        from app.engines.vulnerability.nvd_cve import NVDCVEClient
        client = NVDCVEClient()
        
        # Try a simple request with short timeout
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as HTTPX_CLIENT:
            response = await HTTPX_CLIENT.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"apiKey": client.api_key or ""}
            )
            
        if response.status_code == 200:
            return {"status": "healthy", "api": "NVD", "response_code": 200}
        else:
            return {"status": "degraded", "api": "NVD", "response_code": response.status_code}
    except Exception as e:
        return {"status": "unhealthy", "api": "NVD", "error": str(e)}


async def check_cisa_api() -> dict:
    """
    Check CISA API availability.
    
    Returns:
        dict: CISA API status
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as HTTPX_CLIENT:
            response = await HTTPX_CLIENT.get(
                "https://www.cisa.gov/api/kev_catalog/",
                timeout=5.0
            )
            
        if response.status_code == 200:
            return {"status": "healthy", "api": "CISA KEV", "response_code": 200}
        else:
            return {"status": "degraded", "api": "CISA KEV", "response_code": response.status_code}
    except Exception as e:
        return {"status": "unhealthy", "api": "CISA KEV", "error": str(e)}


async def check_nmap() -> dict:
    """
    Check nmap availability.
    
    Returns:
        dict: Nmap status
    """
    try:
        from app.core.process_manager import check_executable_exists
        
        if check_executable_exists("nmap"):
            # Try to get version
            import subprocess
            try:
                result = subprocess.run(
                    ["nmap", "--version"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    version_line = result.stdout.decode().split("\n")[0]
                    return {
                        "status": "healthy",
                        "tool": "nmap",
                        "version": version_line
                    }
            except Exception:
                pass
            
            return {"status": "healthy", "tool": "nmap"}
        else:
            return {"status": "unhealthy", "tool": "nmap", "error": "not installed"}
    except Exception as e:
        return {"status": "unhealthy", "tool": "nmap", "error": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    from app.database import engine, init_db
    
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
    
    yield

    # Shutdown
    print("Shutting down application")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Network Discovery & Vulnerability Intelligence Platform",
    version=settings.app_version,
    lifespan=lifespan
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Configure CORS with secure defaults
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
    """
    Root endpoint.
    
    Returns basic application information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns a simple status indicator for the application.
    """
    return {"status": "healthy"}


@app.get("/health/extended")
async def extended_health_check():
    """
    Extended health check with dependency status.
    
    Returns detailed status of all system dependencies including:
    - Database connection
    - NVD API availability
    - CISA KEV API availability
    - Nmap tool status
    
    Returns:
        dict: Complete health status with all dependencies
    """
    # Run all health checks concurrently
    results = await asyncio.gather(
        check_database(),
        check_nvd_api(),
        check_cisa_api(),
        check_nmap()
    )
    
    # Determine overall status
    statuses = [r["status"] for r in results]
    
    if "unhealthy" in statuses:
        overall_status = "degraded"
    elif "degraded" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    # Build detailed status report
    detailed_status = {}
    for result in results:
        api_name = result.get("api") or result.get("tool") or "database"
        detailed_status[api_name] = {
            "status": result["status"],
            **{k: v for k, v in result.items() if k != "status"}
        }
    
    return {
        "overall_status": overall_status,
        "timestamp": asyncio.get_event_loop().time(),
        "services": detailed_status
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """
    Global exception handler.
    
    Catches and handles all unhandled exceptions in the application.
    """
    # Get request ID for logging
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log exception with context
    log_context = get_log_context(request)
    print(f"[{request_id}] Exception occurred: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "message": "An internal error occurred",
            "request_id": request_id
        }
    )


# Include routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug
    )
