# NetScope Authentication Module

"""
Authentication and authorization utilities for API endpoints.
"""

import hashlib
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from functools import wraps

import jwt
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from pydantic import BaseModel, Field
from jwt import InvalidTokenError

from .config import settings
from .validators import validate_cidr


# Token schemes
security = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class TokenPayload(BaseModel):
    """Token payload model."""
    sub: str = Field(..., description="Subject (user ID)")
    username: str = Field(..., description="Username")
    scopes: List[str] = Field(default_factory=list, description="User scopes/permissions")
    exp: datetime = Field(..., description="Expiration time")
    iat: Optional[datetime] = Field(None, description="Issued at time")
    nbf: Optional[datetime] = Field(None, description="Not before time")
    fingerprint: Optional[str] = Field(None, description="Client fingerprint for token binding")


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)


class AuthCredentials(BaseModel):
    """Authentication credentials model."""
    valid: bool = False
    user: Optional[User] = None
    scopes: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request, handling proxied requests.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def create_token(data: Dict[str, Any], request: Request = None, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with enhanced security features.
    
    Args:
        data: Payload data to encode
        request: Optional FastAPI request for client fingerprinting
        expires_delta: Optional expiration time delta
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    # Add standard claims
    current_time = datetime.utcnow()
    to_encode.update({
        "exp": expire,
        "iat": current_time,
        "nbf": current_time,  # Not before (immediate)
    })
    
    # Bind token to client fingerprint if request is provided
    if request:
        user_agent = request.headers.get("user-agent", "")
        ip_address = get_client_ip(request)
        fingerprint = f"{ip_address}:{user_agent}"
        to_encode["fingerprint"] = hashlib.sha256(fingerprint.encode()).hexdigest()
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str, request: Request = None) -> Optional[TokenPayload]:
    """
    Verify a JWT token with enhanced security checks.
    
    Args:
        token: JWT token to verify
        request: Optional FastAPI request for fingerprint validation
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        # Decode with strict validation - requires exp, iat, nbf claims
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],  # Only allow configured algorithm (HS256)
            options={"require": ["exp", "iat", "nbf"]}
        )
        
        # Validate expiration time
        exp = payload.get("exp")
        if isinstance(exp, datetime):
            if datetime.utcnow() > exp:
                return None
        
        # Validate not before time
        nbf = payload.get("nbf")
        if isinstance(nbf, datetime):
            if datetime.utcnow() < nbf:
                return None
        
        # Validate issued at time (not in the future)
        iat = payload.get("iat")
        if isinstance(iat, datetime):
            if datetime.utcnow() < iat:
                return None
        
        # Validate fingerprint binding if token was bound and request is provided
        fingerprint = payload.get("fingerprint")
        if fingerprint and request:
            user_agent = request.headers.get("user-agent", "")
            ip_address = get_client_ip(request)
            calculated_fingerprint = hashlib.sha256(
                f"{ip_address}:{user_agent}".encode()
            ).hexdigest()
            
            if calculated_fingerprint != fingerprint:
                return None
        
        # Extract user info
        sub = payload.get("sub")
        username = payload.get("username", "")
        scopes = payload.get("scopes", [])
        
        return TokenPayload(
            sub=str(sub) if sub else "",
            username=username,
            scopes=scopes,
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            nbf=payload.get("nbf"),
            fingerprint=fingerprint
        )
    except jwt.ExpiredSignatureError:
        return None
    except InvalidTokenError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request: Request = None,
) -> Optional[User]:
    """
    Get current authenticated user from token.
    
    Args:
        credentials: HTTP authorization credentials
        request: Optional FastAPI request for token binding validation
        
    Returns:
        User if authenticated, None otherwise
    """
    if not credentials or not credentials.credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token, request)
    
    if not payload:
        return None
    
    return User(
        id=payload.sub,
        username=payload.username,
        scopes=payload.scopes,
    )


def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> User:
    """
    Require authentication for an endpoint.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User if authenticated
        
    Raises:
        HTTPException: If not authenticated
    """
    user = get_current_user(credentials)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_scope(required_scopes: List[str]) -> User:
    """
    Require specific scopes/permissions for an endpoint.
    
    Args:
        required_scopes: List of required scope names
        
    Returns:
        User if authenticated with required scopes
        
    Raises:
        HTTPException: If not authenticated or missing required scopes
    """
    def dependency(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
        user = require_auth(credentials)
        
        if not user.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scopes: {', '.join(required_scopes)}",
            )
        
        # Check if user has any of the required scopes
        has_scope = any(scope in user.scopes for scope in required_scopes)
        
        if not has_scope:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scopes: {', '.join(required_scopes)}",
            )
        
        return user
    
    return Depends(dependency)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    In production, this would check against a database or external auth service.
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        User if authenticated, None otherwise
    """
    # For demo purposes, allow any user with a non-empty password
    if not username or not password:
        return None
    
    # In production, verify against database
    # For now, create a user with default scopes
    return User(
        id="user-" + username,
        username=username,
        email=f"{username}@example.com",
        scopes=["read", "write"] if password != "" else [],
    )


def get_api_key(request: Request) -> Optional[str]:
    """
    Extract API key from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        API key string if present, None otherwise
    """
    return request.headers.get("X-API-Key")


def require_api_key(request: Request) -> str:
    """
    Require API key from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        API key string
        
    Raises:
        HTTPException: If no API key provided
    """
    api_key = get_api_key(request)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
        )
    
    # In production, verify against environment variable or database
    # API keys must be configured via environment variables or a secure secret store
    expected_api_key = os.environ.get("API_KEY")
    
    if expected_api_key and api_key == expected_api_key:
        return api_key
    
    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )


# Default authorized scopes
DEFAULT_SCOPES = {
    "read": "Read access",
    "write": "Write access",
    "admin": "Administrative access",
}


def get_scopes_for_user(user: User) -> List[str]:
    """
    Get list of scopes for a user.
    
    Args:
        user: User object
        
    Returns:
        List of scope names
    """
    return user.scopes or []


# Token expiration time
TOKEN_EXPIRY_MINUTES = settings.access_token_expire_minutes


def create_auth_token_for_user(user: User) -> str:
    """
    Create an authentication token for a user.
    
    Args:
        user: User object
        
    Returns:
        JWT token string
    """
    return create_token(
        data={
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "scopes": user.scopes or [],
        },
        expires_delta=timedelta(minutes=TOKEN_EXPIRY_MINUTES),
    )
