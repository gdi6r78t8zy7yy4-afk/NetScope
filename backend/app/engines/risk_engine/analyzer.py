# NetScope Risk Analyzer

"""
Risk analysis and prioritization engine.
"""

from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class RiskAnalyzer:
    """
    Analyze and prioritize risks based on multiple factors.

    Considers:
    - CVSS score
    - CISA KEV status
    - EPSS scores
    - Asset exposure
    - Confidence level
    """

    def __init__(self):
        self.logger = logger.bind(analyzer="risk")

    async def analyze_risk(
        self, finding: Dict, asset_info: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze risk for a vulnerability finding.

        Args:
            finding: Vulnerability finding
            asset_info: Asset information

        Returns:
            Risk analysis
        """
        self.logger.info("Analyzing risk", cve=finding.get("cve_id"))

        # Base CVSS score
        cvss_score = finding.get("cvss_score", 0)

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            cvss_score,
            finding.get("kev_status", "not_kev"),
            finding.get("epss_score", 0),
            finding.get("confidence", 0.5),
        )

        # Determine priority
        priority = self._determine_priority(risk_score)

        return {
            "cve_id": finding.get("cve_id"),
            "ip_address": asset_info.get("ip_address") if asset_info else None,
            "cvss_score": cvss_score,
            "kev_status": finding.get("kev_status", "not_kev"),
            "epss_score": finding.get("epss_score"),
            "confidence": finding.get("confidence", 0.5),
            "risk_score": risk_score,
            "priority": priority,
        }

    def _calculate_risk_score(
        self, cvss: float, kev_status: str, epss: float, confidence: float
    ) -> int:
        """
        Calculate overall risk score (0-100).

        Args:
            cvss: CVSS score (0-10)
            kev_status: CISA KEV status
            epss: EPSS score (0-1)
            confidence: Match confidence

        Returns:
            Risk score
        """
        # Base score from CVSS (0-40 points)
        cvss_score = int(cvss * 4)

        # KEV boost (0-30 points)
        if kev_status == "kev":
            kev_score = 30
        else:
            kev_score = int(cvss * 2)

        # EPSS factor (0-15 points)
        epss_score = int(epss * 15)

        # Confidence factor (0-15 points)
        confidence_score = int(confidence * 15)

        total = cvss_score + kev_score + epss_score + confidence_score

        return min(100, total)

    def _determine_priority(self, risk_score: int) -> str:
        """
        Determine priority level based on risk score.

        Args:
            risk_score: Risk score (0-100)

        Returns:
            Priority level
        """
        if risk_score >= 80:
            return "critical"
        elif risk_score >= 60:
            return "high"
        elif risk_score >= 40:
            return "medium"
        else:
            return "low"

    async def analyze_asset_risks(
        self,
        asset_ip: str,
        findings: List[Dict],
        kev_catalog: Optional[List[str]] = None,
    ) -> Dict:
        """
        Analyze all risks for an asset.

        Args:
            asset_ip: Asset IP address
            findings: List of vulnerability findings
            kev_catalog: Optional KEV CVE list

        Returns:
            Asset risk analysis
        """
        self.logger.info(
            "Analyzing asset risks", ip=asset_ip, finding_count=len(findings)
        )

        # Get KEV status for each finding
        kev_set = set(kev_catalog or [])

        risk_findings = []

        for finding in findings:
            cve = finding.get("cve_id", "")

            # Check KEV status
            kev_status = "kev" if cve in kev_set else "not_kev"

            risk = await self.analyze_risk(
                {**finding, "kev_status": kev_status}, {"ip_address": asset_ip}
            )

            risk_findings.append(risk)

        # Sort by risk score
        risk_findings.sort(key=lambda x: x["risk_score"], reverse=True)

        # Calculate summary
        critical_count = sum(
            1 for r in risk_findings if r["priority"] == "critical")
        high_count = sum(1 for r in risk_findings if r["priority"] == "high")
        medium_count = sum(
            1 for r in risk_findings if r["priority"] == "medium")
        low_count = sum(1 for r in risk_findings if r["priority"] == "low")

        return {
            "ip_address": asset_ip,
            "total_findings": len(risk_findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "risk_findings": risk_findings,
        }

    async def get_top_risks(
        self,
        asset_ip: str,
        findings: List[Dict],
        kev_catalog: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get the top N risk findings.

        Args:
            asset_ip: Asset IP
            findings: Vulnerability findings
            kev_catalog: KEV CVE list
            limit: Number of top risks to return

        Returns:
            List of top risk findings
        """
        analysis = await self.analyze_asset_risks(asset_ip, findings, kev_catalog)

        return analysis["risk_findings"][:limit]

    async def get_risk_distribution(
        self,
        asset_ip: str,
        findings: List[Dict],
        kev_catalog: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get risk distribution summary.

        Args:
            asset_ip: Asset IP
            findings: Vulnerability findings
            kev_catalog: KEV CVE list

        Returns:
            Risk distribution
        """
        analysis = await self.analyze_asset_risks(asset_ip, findings, kev_catalog)

        return {
            "total": len(analysis["risk_findings"]),
            "by_priority": {
                "critical": analysis["critical_count"],
                "high": analysis["high_count"],
                "medium": analysis["medium_count"],
                "low": analysis["low_count"],
            },
        }
