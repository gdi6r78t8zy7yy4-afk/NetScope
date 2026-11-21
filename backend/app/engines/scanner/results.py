# NetScope Scan Results Processing

"""
Scan results aggregation and summary generation.
"""

from typing import List, Dict, Any
from collections import defaultdict


def aggregate_scan_results(scan_results: List[dict]) -> dict:
    """
    Aggregate multiple scan results into a summary.

    Args:
        scan_results: List of individual scan results

    Returns:
        Aggregated results dictionary
    """
    aggregated = {
        "total_hosts": 0,
        "hosts_up": 0,
        "hosts_down": 0,
        "total_ports_found": 0,
        "by_ip": {},
    }

    for result in scan_results:
        ip = result.get("ip", "unknown")

        aggregated["total_hosts"] += 1

        # Track host status
        if result.get("status") == "up":
            aggregated["hosts_up"] += 1
        else:
            aggregated["hosts_down"] += 1

        # Count ports
        ports = result.get("ports", [])
        port_count = sum(1 for p in ports if p.get("state") == "open")
        aggregated["total_ports_found"] += port_count

        # Store by IP
        aggregated["by_ip"][ip] = {
            "status": result.get("status", "unknown"),
            "open_ports": port_count,
            "services": [
                p.get("service")
                for p in ports
                if p.get("state") == "open" and p.get("service")
            ],
        }

    return aggregated


def generate_scan_summary(scan_data: dict) -> dict:
    """
    Generate a summary of scan results.

    Args:
        scan_data: Scan data dictionary

    Returns:
        Summary dictionary
    """
    summary = {
        "scan_id": scan_data.get("scan_id", 0),
        "target": scan_data.get("target", "unknown"),
        "scan_type": scan_data.get("scan_type", "unknown"),
        "duration": f"{scan_data.get('duration_seconds', 0)} seconds",
        "timestamp": scan_data.get("timestamp", ""),
    }

    # Statistics
    stats = {
        "total_hosts": scan_data.get("total_hosts", 0),
        "hosts_up": scan_data.get("hosts_up", 0),
        "hosts_down": scan_data.get("hosts_down", 0),
        "host_success_rate": 0.0,
    }

    if stats["total_hosts"] > 0:
        stats["host_success_rate"] = round(
            (stats["hosts_up"] / stats["total_hosts"]) * 100, 2
        )

    # Port statistics
    ports_found = scan_data.get("ports_found", [])
    stats["unique_ports"] = len(ports_found)

    # Severity summary
    findings = scan_data.get("findings", [])
    severity_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for finding in findings:
        severity = finding.get("severity", "low").lower()
        if severity in severity_summary:
            severity_summary[severity] += 1

    summary["statistics"] = stats
    summary["severity_summary"] = severity_summary
    summary["total_findings"] = len(findings)

    return summary


def generate_vulnerability_summary(findings: List[dict]) -> dict:
    """
    Generate a vulnerability summary.

    Args:
        findings: List of vulnerability findings

    Returns:
        Vulnerability summary dictionary
    """
    if not findings:
        return {
            "total_findings": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "affected_hosts": set(),
            "unique_cves": set(),
        }

    summary = {
        "total_findings": len(findings),
        "by_severity": defaultdict(int),
        "affected_hosts": set(),
        "unique_cves": set(),
    }

    for finding in findings:
        # Count by severity
        severity = finding.get("severity", "low").lower()
        summary["by_severity"][severity] += 1

        # Track affected hosts
        if "ip" in finding:
            summary["affected_hosts"].add(finding["ip"])

        # Track unique CVEs
        cve_id = finding.get("cve_id")
        if cve_id:
            summary["unique_cves"].add(cve_id)

    # Convert sets to lists for JSON serialization
    summary["affected_hosts"] = list(summary["affected_hosts"])
    summary["unique_cves"] = list(summary["unique_cves"])

    # Convert defaultdict to dict
    summary["by_severity"] = dict(summary["by_severity"])

    return summary


def calculate_risk_score(findings: List[dict]) -> dict:
    """
    Calculate risk scores for findings.

    Args:
        findings: List of vulnerability findings

    Returns:
        Risk scores by host
    """
    # Severity weights
    severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}

    risk_by_host = defaultdict(int)

    for finding in findings:
        severity = finding.get("severity", "low").lower()
        weight = severity_weights.get(severity, 1)

        if "ip" in finding:
            risk_by_host[finding["ip"]] += weight

    # Sort by risk score
    sorted_risks = dict(
        sorted(
            risk_by_host.items(),
            key=lambda x: x[1],
            reverse=True))

    return {"total_risk": sum(sorted_risks.values()), "by_host": sorted_risks}


def filter_findings(findings: List[dict], **filters) -> List[dict]:
    """
    Filter findings by criteria.

    Args:
        findings: List of findings
        **filters: Filter criteria

    Returns:
        Filtered list of findings
    """
    filtered = findings

    if "severity" in filters:
        severity = filters["severity"].lower()
        filtered = [
            f for f in filtered if f.get(
                "severity",
                "").lower() == severity]

    if "ip" in filters:
        ip = filters["ip"]
        filtered = [f for f in filtered if f.get("ip") == ip]

    if "cve_id" in filters:
        cve = filters["cve_id"]
        filtered = [f for f in filtered if f.get("cve_id") == cve]

    return filtered
