# NetScope Configuration Validation Tests

"""
Tests for environment variable validation and configuration.
"""

import pytest
import os


def test_validate_required_env_vars_missing():
    """Test validation detects missing environment variables."""
    from app.core.config import validate_required_env_vars, REQUIRED_ENV_VARS
    
    # Ensure SECRET_KEY is not set
    original_value = os.environ.get("SECRET_KEY")
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]
    
    try:
        # Call with raise_error=False to get results without raising
        result = validate_required_env_vars(raise_error=False)
        
        assert result["status"] == "invalid"
        assert "SECRET_KEY" in result["missing"]
        
        # Now test with raise_error=True
        with pytest.raises(EnvironmentError) as exc_info:
            validate_required_env_vars(raise_error=True)
        
        # Check that the error message contains required variables
        assert "SECRET_KEY" in str(exc_info.value)
        assert "required environment variables" in str(exc_info.value).lower()
    finally:
        # Restore original value
        if original_value is not None:
            os.environ["SECRET_KEY"] = original_value


def test_validate_required_env_vars_present():
    """Test validation passes when all required vars are present."""
    from app.core.config import validate_required_env_vars
    
    # Set a dummy secret key
    original_value = os.environ.get("SECRET_KEY")
    os.environ["SECRET_KEY"] = "test-secret-key-for-validation"
    
    try:
        result = validate_required_env_vars(raise_error=False)
        
        assert result["status"] == "valid"
        assert result["missing_count"] == 0
        assert "SECRET_KEY" in result["present"]
    finally:
        # Restore original value
        if original_value is not None:
            os.environ["SECRET_KEY"] = original_value
        else:
            del os.environ["SECRET_KEY"]


def test_settings_validation():
    """Test that Settings validates required env vars on initialization."""
    from app.core.config import Settings, REQUIRED_ENV_VARS
    
    # Set required variables
    original_values = {}
    for var in REQUIRED_ENV_VARS:
        original_values[var] = os.environ.get(var)
        os.environ[var] = f"test-{var}-value"
    
    try:
        # This should not raise since validate_required_env_vars is called
        # during module import with settings = get_settings() 
        # We can test the Settings class directly
        settings = Settings()
        assert settings is not None
    finally:
        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]


def test_request_id_generation():
    """Test request ID middleware generates unique IDs."""
    from app.middleware.request_id import generate_request_id
    
    # Generate multiple IDs
    ids = [generate_request_id() for _ in range(10)]
    
    # All IDs should be unique
    assert len(set(ids)) == 10
    
    # Each ID should have expected format
    for id in ids:
        assert id.startswith("req-")
        assert len(id) > 10
