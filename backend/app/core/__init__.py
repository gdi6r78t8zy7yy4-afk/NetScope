# NetScope Core Module

"""
Core functionality and utilities for the NetScope backend.
"""

from app.core.config import settings
from app.core.security import hash_password, verify_password

__all__ = ["settings", "hash_password", "verify_password"]
