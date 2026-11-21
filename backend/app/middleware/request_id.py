# NetScope Request ID Middleware

"""
Middleware to generate and track request IDs for logging context.
"""

import uuid
from starlette.datastructures import Headers


# Request-local storage (using request.state)
def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        str: Unique request identifier
    """
    return f"req-{uuid.uuid4().hex[:12]}"


def get_request_id(request) -> str:
    """
    Get the request ID from a request object.

    Args:
        request: FastAPI Request object

    Returns:
        str: Request ID
    """
    return getattr(request.state, "request_id", "unknown")


def set_request_id(request, request_id: str) -> None:
    """
    Set the request ID on a request object.

    Args:
        request: FastAPI Request object
        request_id: Request ID to set
    """
    request.state.request_id = request_id


class RequestIDMiddleware:
    """
    Middleware that adds a unique request ID to each request.

    The request ID is stored in the request state and can be accessed
    via logging context for traceability.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """ASGI callable for middleware."""

        # Create a copy of the scope
        async def wrapped_receive():
            return await receive()

        async def wrapped_send(message):
            # Add request ID to response headers
            if message["type"] == "http.response.start":
                # Find request from scope
                if hasattr(scope, "get"):
                    request_id = scope.get("request_id", "unknown")
                else:
                    request_id = getattr(scope, "request_id", "unknown")

                headers = Headers(scope=scope)
                new_headers = [(b"X-Request-ID", request_id.encode())]
                if b"headers" in message:
                    new_headers.extend(message["headers"])
                message = {**message, "headers": new_headers}

            await send(message)

        # Generate unique request ID
        request_id = generate_request_id()

        # Store in scope for later access
        if hasattr(scope, "__setitem__"):
            scope["request_id"] = request_id

        # Call next middleware with modified scope
        await self.app(scope, wrapped_receive, wrapped_send)


async def add_request_id_middleware(app, scope, receive, send):
    """
    Add request ID middleware to ASGI application.

    Args:
        app: ASGI application
        scope: Request scope
        receive: Receive callable
        send: Send callable
    """
    # Generate unique request ID
    request_id = generate_request_id()

    # Store in scope for later access
    if hasattr(scope, "__setitem__"):
        scope["request_id"] = request_id

    # Call next middleware
    await app(scope, receive, send)


def add_request_id_middleware(app):
    """
    Add request ID middleware to FastAPI application.

    Args:
        app: FastAPI application instance
    """

    # Add request ID header to all responses via response middleware
    @app.middleware("http")
    async def request_id_middleware(request, call_next):
        # Generate unique request ID
        request_id = generate_request_id()

        # Store in request state for access in handlers
        set_request_id(request, request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def get_log_context(request=None) -> dict:
    """
    Get logging context including request ID and user info.

    Args:
        request: Optional FastAPI Request object

    Returns:
        dict: Context dictionary for logging
    """
    context = {
        "request_id": get_request_id(request) if request else "unknown",
    }

    return context
