# NetScope Export Functionality Tests

"""
Tests for export functionality.
"""

import pytest
import json
from io import StringIO


def test_csv_export_asset_list():
    """Test CSV export of asset list."""
    from app.utils.export import export_to_csv
    
    assets = [
        {"ip_address": "192.168.1.1", "hostname": "router", "os": "Linux"},
        {"ip_address": "192.168.1.10", "hostname": "server", "os": "Windows"}
    ]
    
    csv_data = export_to_csv(assets, ["ip_address", "hostname", "os"])
    
    assert isinstance(csv_data, str)
    assert "ip_address,hostname,os" in csv_data
    assert "192.168.1.1,router,Linux" in csv_data


def test_csv_export_empty():
    """Test CSV export with no data."""
    from app.utils.export import export_to_csv
    
    assets = []
    
    csv_data = export_to_csv(assets, ["ip_address", "hostname"])
    
    assert isinstance(csv_data, str)
    assert "ip_address,hostname" in csv_data


def test_json_export_scan_results():
    """Test JSON export of scan results."""
    from app.utils.export import export_to_json
    
    results = {
        "scan_id": 1,
        "target": "192.168.1.0/24",
        "host_count": 5,
        "ports_found": [22, 80, 443],
        "findings": [
            {"ip": "192.168.1.1", "port": 443, "service": "https"}
        ]
    }
    
    json_data = export_to_json(results)
    
    assert isinstance(json_data, str)
    parsed = json.loads(json_data)
    assert parsed["target"] == "192.168.1.0/24"
    assert parsed["host_count"] == 5


def test_pdf_report_generation():
    """Test PDF report generation."""
    from app.utils.export import generate_pdf_report
    
    report_data = {
        "title": "Network Scan Report",
        "date": "2026-11-16",
        "summary": {
            "total_hosts": 10,
            "vulnerabilities_found": 3,
            "critical_findings": 1
        },
        "hosts": [
            {"ip": "192.168.1.1", "hostname": "router", "status": "online"}
        ]
    }
    
    pdf_bytes = generate_pdf_report(report_data)
    
    assert isinstance(pdf_bytes, bytes)
    # PDF files start with %PDF
    assert pdf_bytes.startswith(b"%PDF")


def test_export_file_formats():
    """Test supported export formats."""
    from app.utils.export import SUPPORTED_FORMATS
    
    assert "csv" in SUPPORTED_FORMATS
    assert "json" in SUPPORTED_FORMATS
    assert "pdf" in SUPPORTED_FORMATS


def test_export_validation():
    """Test export data validation."""
    from app.utils.export import validate_export_data
    
    # Valid data
    valid_data = {"ip_address": "192.168.1.1", "hostname": "test"}
    assert validate_export_data(valid_data) is True
    
    # Empty data
    empty_data = {}
    assert validate_export_data(empty_data) is True
    
    # Invalid type
    invalid_data = "not a dict"
    assert validate_export_data(invalid_data) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
