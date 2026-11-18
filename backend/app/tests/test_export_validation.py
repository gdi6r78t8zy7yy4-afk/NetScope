# NetScope Export Validation Tests

"""
Tests for export format validation functionality.
"""

import pytest


def test_validate_export_format_valid():
    """Test validate_export_format with valid formats."""
    from app.utils.export import validate_export_format
    
    assert validate_export_format("csv") is True
    assert validate_export_format("CSV") is True  # Case insensitive
    assert validate_export_format("json") is True
    assert validate_export_format("JSON") is True
    assert validate_export_format("pdf") is True
    assert validate_export_format("PDF") is True


def test_validate_export_format_invalid():
    """Test validate_export_format with invalid formats."""
    from app.utils.export import validate_export_format
    
    assert validate_export_format("xml") is False
    assert validate_export_format("txt") is False
    assert validate_export_format("html") is False
    assert validate_export_format("") is False


def test_validate_export_data():
    """Test validate_export_data function."""
    from app.utils.export import validate_export_data
    
    # Valid data
    assert validate_export_data({"key": "value"}) is True
    assert validate_export_data([{"key": "value"}]) is True
    assert validate_export_data([]) is True
    
    # Invalid data
    assert validate_export_data(None) is False
    assert validate_export_data("string") is False
    assert validate_export_data(123) is False
    assert validate_export_data(object()) is False


def test_validate_export_parameters():
    """Test validate_export_parameters function."""
    from app.utils.export import validate_export_parameters
    
    # Valid parameters
    is_valid, error = validate_export_parameters("csv", [{"key": "value"}])
    assert is_valid is True
    assert error is None
    
    is_valid, error = validate_export_parameters("json", {"key": "value"})
    assert is_valid is True
    assert error is None
    
    # Invalid format
    is_valid, error = validate_export_parameters("xml", [{"key": "value"}])
    assert is_valid is False
    assert error is not None
    assert "xml" in str(error).lower() or "csv" in str(error)
    
    # Invalid data
    is_valid, error = validate_export_parameters("csv", None)
    assert is_valid is False
    assert error is not None
    
    # Empty data for CSV (should fail)
    is_valid, error = validate_export_parameters("csv", [])
    assert is_valid is False
    assert "empty" in str(error).lower()


def test_export_to_csv_validation():
    """Test export_to_csv with data validation."""
    from app.utils.export import export_to_csv
    
    # Valid CSV export
    result = export_to_csv([{"name": "test", "value": 123}])
    assert "name,value" in result
    assert "test,123" in result
    
    # Single dict export
    result = export_to_csv({"name": "test", "value": 123})
    assert "name,value" in result
    assert "test,123" in result


def test_export_to_json_validation():
    """Test export_to_json with data validation."""
    from app.utils.export import export_to_json
    import json
    
    # Valid JSON export
    result = export_to_json([{"key": "value"}])
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["key"] == "value"
    
    # Single dict export
    result = export_to_json({"key": "value"})
    parsed = json.loads(result)
    assert parsed["key"] == "value"


def test_create_export_filename():
    """Test create_export_filename function."""
    from app.utils.export import create_export_filename
    
    filename = create_export_filename("report", "csv")
    assert filename.startswith("report_")
    assert filename.endswith(".csv")
    
    filename = create_export_filename("scan_results", "json")
    assert filename.startswith("scan_results_")
    assert filename.endswith(".json")
