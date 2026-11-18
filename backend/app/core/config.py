# NetScope Configuration Module

"""
Application configuration management using Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass
import os
from typing import Optional, List

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Required environment variables that must be set for startup
REQUIRED_ENV_VARS = [
    "SECRET_KEY",
]


def validate_required_env_vars(raise_error: bool = True) -> dict:
    """
    Validate that all required environment variables are set.
    
    Args:
        raise_error: If True, raises EnvironmentError when vars are missing
                    If False, returns results without raising
            
    Returns:
        dict: Validation results with status and missing variables
        
    Raises:
        EnvironmentError: If required environment variables are missing
                          and raise_error is True
    """
    missing_vars = []
    present_vars = []
    
    for var in REQUIRED_ENV_VARS:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            present_vars.append(var)
    
    results = {
        "status": "valid" if not missing_vars else "invalid",
        "required_count": len(REQUIRED_ENV_VARS),
        "present_count": len(present_vars),
        "missing_count": len(missing_vars),
        "present": present_vars,
        "missing": missing_vars,
    }
    
    if missing_vars and raise_error:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"\nRequired variables ({len(REQUIRED_ENV_VARS)} total):\n"
        )
        for var in REQUIRED_ENV_VARS:
            error_msg += f"  - {var}\n"
        error_msg += (
            f"\nMissing variables ({len(missing_vars)} total):\n"
        )
        for var in missing_vars:
            error_msg += f"  - {var} (NOT SET)\n"
        error_msg += (
            "\nPlease set these variables in your .env file or environment.\n"
        )
        
        raise EnvironmentError(error_msg)
    
    return results


def validate_secret_key(secret_key: str) -> str:
    """
    Validate secret key meets security requirements.
    
    Args:
        secret_key: Secret key string to validate
        
    Returns:
        str: The validated secret key
        
    Raises:
        ValueError: If secret key doesn't meet requirements
    """
    if not secret_key:
        raise ValueError("SECRET_KEY cannot be empty")
    
    # Check minimum length
    if len(secret_key) < 32:
        raise ValueError(
            "SECRET_KEY must be at least 32 characters long for security. "
            "Generate a secure key using: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    # Check for default placeholder values
    insecure_defaults = [
        "your-secret-key-change-in-production",
        "changeme",
        "password",
        "secret",
        "default",
    ]
    
    if secret_key.lower() in insecure_defaults:
        raise ValueError(
            "SECRET_KEY must not be a default placeholder value. "
            "Generate a secure key using: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    # In production, require environment variable
    if not os.environ.get("ENV_FILE_LOADED", False):
        import warnings
        warnings.warn(
            "SECRET_KEY is set but ENV_FILE_LOADED is not. "
            "Consider using a .env file for secret management.",
            UserWarning
        )
    
    return secret_key


def get_secret_key() -> str:
    """
    Get secret key from environment or generate a warning.
    
    Returns:
        str: Secret key value
    """
    secret_key = os.environ.get("SECRET_KEY")
    
    if not secret_key:
        # Check for .env file
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            import warnings
            warnings.warn(
                "SECRET_KEY not found in environment variables. "
                "Create a .env file with SECRET_KEY set to a secure random value.",
                UserWarning
            )
        else:
            raise ValueError(
                "SECRET_KEY environment variable must be set. "
                "Create a .env file with SECRET_KEY or run: "
                "echo 'SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")' > .env"
            )
        
        raise EnvironmentError(
            "SECRET_KEY is required for startup. "
            "Create a .env file with SECRET_KEY set to a secure random value.\n"
            "Generate one using: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    # Validate the key
    return validate_secret_key(secret_key)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "NetScope"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Backend server
    backend_host: str = "localhost"
    backend_port: int = 8000
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/netscope.db"
    
    # Security
    @computed_field
    @property
    def secret_key(self) -> str:
        """Get validated secret key."""
        return get_secret_key()
    
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Security - CORS origins (comma-separated for environment variable)
    allowed_origins: Optional[str] = None
    
    # Scanning
    default_rate_limit: str = "medium"
    max_concurrent_hosts: int = 5
    scan_timeout_seconds: int = 3600
    
    # Intelligence Sources
    cisa_api_key: Optional[str] = None
    nvd_api_key: Optional[str] = None
    intelligence_update_interval_hours: int = 24
    
    # Dependencies
    nmap_required: bool = True
    arp_scan_required: bool = False
    tshark_optional: bool = True
    
    @property
    def data_dir(self) -> Path:
        """Return the data directory path."""
        return Path(__file__).parent.parent.parent / "data"
    
    @property
    def log_dir(self) -> Path:
        """Return the log directory path."""
        return Path(__file__).parent.parent.parent / "logs"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug
    
    @property
    def environment(self) -> str:
        """Get environment name."""
        return "production" if not self.debug else "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
