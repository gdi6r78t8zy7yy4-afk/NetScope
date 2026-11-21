# NetScope Security Module

"""
Security utilities for password hashing and token generation.
"""

import hashlib
import secrets
from typing import Optional

# Argon2 parameters (industry standard)
# Using passlib which is already in requirements
try:
    from passlib.hash import argon2

    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False


def hash_password(
        password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password using Argon2 if available, otherwise PBKDF2 with SHA256.

    Argon2 is the winner of the Password Hashing Competition (PHC) and is
    considered the industry standard for password hashing due to:
    - Memory-hardness (resistant to GPU/ASIC attacks)
    - Parallelism support
    - Flexible cost parameters

    PBKDF2 with 600,000 iterations is used as fallback.

    Args:
        password: Plain text password to hash
        salt: Optional salt string. If None, a secure random salt is generated.

    Returns:
        Tuple of (hashed_password, salt)

    Raises:
        ValueError: If password is empty or too long
    """
    # Validate password length
    if not password:
        raise ValueError("Password cannot be empty")

    if len(password) > 1024:
        raise ValueError("Password exceeds maximum length of 1024 characters")

    # Validate salt if provided
    if salt is not None and len(salt) < 16:
        raise ValueError("Salt must be at least 16 characters for security")

    if salt is None:
        salt = secrets.token_hex(32)  # 256-bit random salt

    # Use Argon2 if available (industry standard)
    if ARGON2_AVAILABLE:
        try:
            # Argon2id is recommended for password hashing
            # Parameters: memory_cost=65536 (64MB), time_cost=3, parallelism=4
            hashed = argon2.using(
                memory_cost=65536, time_cost=3, parallelism=4, salt_len=32, hash_len=32
            ).hash(password)
            return hashed, salt
        except Exception:
            # Fall back to PBKDF2 if Argon2 fails
            pass

    # Fallback: PBKDF2 with SHA256 and increased iterations (600,000)
    # This meets NIST SP 800-132 recommendations for password hashing
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        600_000,  # Increased from 100,000 to meet current security standards
    )

    return password_hash.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against its hash and salt.

    Supports both Argon2 hashes (stored as single string) and PBKDF2 hashes.

    Args:
        password: Plain text password to verify
        hashed_password: Stored hash (may be Argon2 format or PBKDF2 hex)
        salt: Salt used during hashing

    Returns:
        True if password matches, False otherwise
    """
    # Validate inputs
    if not password:
        return False

    try:
        # Check if hash is Argon2 format (starts with $argon2)
        if hashed_password.startswith("$argon2"):
            try:
                return argon2.verify(password, hashed_password)
            except Exception:
                return False

        # PBKDF2 hash verification
        computed_hash, _ = hash_password(password, salt)
        return secrets.compare_digest(computed_hash, hashed_password)
    except Exception:
        return False


def check_password_strength(password: str) -> dict:
    """
    Check password strength and return recommendations.

    Implements OWASP password strength guidelines:
    - Minimum 12 characters
    - Contains uppercase, lowercase, numbers, and special chars
    - Not in common password list

    Args:
        password: Password to check

    Returns:
        Dictionary with strength score and recommendations
    """
    if not password:
        return {
            "score": 0,
            "valid": False,
            "message": "Password cannot be empty",
            "recommendations": ["Enter a password to check its strength"],
        }

    score = 0
    recommendations = []

    # Length checks (OWASP minimum)
    if len(password) >= 12:
        score += 20
    elif len(password) >= 8:
        score += 10
        recommendations.append(
            "Increase password length to at least 12 characters")
    else:
        score += 5
        recommendations.append(
            "Increase password length to at least 12 characters")

    # Character variety checks
    has_lowercase = any(c.islower() for c in password)
    has_uppercase = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() and not c.isspace() for c in password)

    if has_lowercase:
        score += 15
    else:
        recommendations.append("Add lowercase letters")

    if has_uppercase:
        score += 15
    else:
        recommendations.append("Add uppercase letters")

    if has_digit:
        score += 15
    else:
        recommendations.append("Add numbers")

    if has_special:
        score += 20
    else:
        recommendations.append("Add special characters (!@#$%^&*)")

    # Common password check (simplified)
    common_passwords = [
        "password",
        "12345678",
        "qwerty",
        "admin",
        "welcome",
        "password123",
        "letmein",
    ]

    if password.lower() in common_passwords:
        score = min(score, 30)
        recommendations.append("Avoid common passwords")

    # Determine if password is valid
    valid = score >= 60

    return {
        "score": min(score, 100),
        "valid": valid,
        "recommendations": recommendations,
    }


def generate_secure_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        input_str: User-provided string

    Returns:
        Sanitized string
    """
    # Remove potentially dangerous characters
    dangerous_chars = [";", "|", "$", "`", ">", "<"]
    return "".join(c for c in input_str if c not in dangerous_chars)
