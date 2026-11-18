# NetScope Scan Results Processing Tests

"""
Tests for scan results processing.
"""

import pytest


def test_nmap_xml_parsing_basic():
    """Test basic Nmap XML parsing."""
    from app.engines.scanner.parser import parse_nmap_xml
    
    nmap_output = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV 192.168.1.1" start="1731745200">
  <host><status state="up"/></host>
  <runstats><finished time="1731745260"/></runstats>
</nmaprun>"""
    
    result = parse_nmap_xml(nmap_output)
    
    assert "hosts" in result
    assert len(result["hosts"]) == 1


def test_nmap_xml_parsing_with_ports():
    """Test Nmap XML parsing with port information."""
    from app.engines.scanner.parser import parse_nmap_xml
    
    nmap_output = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV 192.168.1.10">
  <host>
    <address addr="192.168.1.10" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    
    result = parse_nmap_xml(nmap_output)
    
    assert "ports" in result
    assert len(result["ports"]) == 2
    
    ports_dict = {p["port"]: p for p in result["ports"]}
    assert 22 in ports_dict
    assert 80 in ports_dict
    assert ports_dict[22]["service"] == "ssh"


def test_nmap_xml_parsing_os_detection():
    """Test Nmap XML parsing with OS detection."""
    from app.engines.scanner.parser import parse_nmap_xml
    
    nmap_output = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -O 192.168.1.5">
  <host>
    <os>
      <osmatch name="Linux" accuracy="95"/>
    </os>
  </host>
</nmaprun>"""
    
    result = parse_nmap_xml(nmap_output)
    
    assert "os" in result
    assert len(result["os"]) > 0


def test_scan_results_aggregation():
    """Test scan results aggregation."""
    from app.engines.scanner.results import aggregate_scan_results
    
    individual_results = [
        {"ip": "192.168.1.1", "status": "up", "ports": []},
        {"ip": "192.168.1.2", "status": "up", "ports": []},
        {"ip": "192.168.1.3", "status": "down", "ports": []}
    ]
    
    aggregated = aggregate_scan_results(individual_results)
    
    assert aggregated["total_hosts"] == 3
    assert aggregated["hosts_up"] == 2


def test_scan_summary_generation():
    """Test scan summary generation."""
    from app.engines.scanner.results import generate_scan_summary
    
    scan_data = {
        "scan_id": 1,
        "target": "192.168.1.0/24",
        "scan_type": "port_scan",
        "duration_seconds": 120,
        "total_hosts": 50,
        "hosts_up": 10,
        "ports_found": [22, 80, 443],
        "findings": []
    }
    
    summary = generate_scan_summary(scan_data)
    
    assert "statistics" in summary
    assert summary["target"] == "192.168.1.0/24"


def test_vulnerability_summary():
    """Test vulnerability summary generation."""
    from app.engines.scanner.results import generate_vulnerability_summary
    
    findings = [
        {"ip": "192.168.1.1", "cve_id": "CVE-2024-1234", "severity": "high"},
        {"ip": "192.168.1.2", "cve_id": "CVE-2024-5678", "severity": "medium"},
        {"ip": "192.168.1.3", "cve_id": "CVE-2024-9012", "severity": "low"}
    ]
    
    summary = generate_vulnerability_summary(findings)
    
    assert summary["total_findings"] == 3
    assert summary["by_severity"]["high"] == 1


def test_parse_nmap_xml_invalid():
    """Test Nmap XML parsing with invalid input."""
    from app.engines.scanner.parser import parse_nmap_xml
    
    # Invalid XML
    result = parse_nmap_xml("not valid xml")
    assert isinstance(result, dict)
    
    # Empty input
    result = parse_nmap_xml("")
    assert isinstance(result, dict)


def test_risk_score_calculation():
    """Test risk score calculation."""
    from app.engines.scanner.results import calculate_risk_score
    
    findings = [
        {"ip": "192.168.1.1", "severity": "critical"},
        {"ip": "192.168.1.1", "severity": "high"},
        {"ip": "192.168.1.2", "severity": "low"}
    ]
    
    risk = calculate_risk_score(findings)
    
    assert "by_host" in risk
    assert risk["total_risk"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
