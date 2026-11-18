# NetScope Asset Correlator

"""
Asset-level vulnerability correlation.
"""

from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class AssetCorrelator:
    """
    Correlate vulnerabilities with assets (hosts).
    """
    
    def __init__(self):
        self.logger = logger.bind(correlator="asset")
    
    async def correlate_asset(
        self,
        ip_address: str,
        services: List[Dict],
        vuln_database: List[Dict]
    ) -> List[Dict]:
        """
        Correlate vulnerabilities for a single asset.
        
        Args:
            ip_address: Asset IP address
            services: List of detected services
            vuln_database: Vulnerability database
            
        Returns:
            List of potential vulnerabilities
        """
        self.logger.info(
            "Correlating asset",
            ip=ip_address,
            service_count=len(services)
        )
        
        findings = []
        
        for vuln in vuln_database:
            match = self._match_vuln_to_asset(vuln, services)
            
            if match:
                findings.append({
                    "ip_address": ip_address,
                    **match
                })
        
        return findings
    
    def _match_vuln_to_asset(
        self,
        vuln: Dict,
        services: List[Dict]
    ) -> Optional[Dict]:
        """Match vulnerability to asset services."""
        vuln_cpe = vuln.get("cpe_match", "").lower()
        
        for service in services:
            product = service.get("product", "")
            
            if self._cpe_matches_product(vuln_cpe, product):
                return {
                    "cve_id": vuln.get("cve_id"),
                    "confidence": self._calculate_confidence(
                        vuln,
                        service
                    ),
                    "evidence": self._generate_evidence(vuln, service)
                }
        
        return None
    
    def _cpe_matches_product(self, cpe: str, product: str) -> bool:
        """Check if CPE matches a product."""
        if not cpe or not product:
            return False
        
        # CPE format: cpe:2.3:a:vendor:product:*:*:...
        if "cpe:" in cpe:
            parts = cpe.lower().split(":")
            if len(parts) >= 4:
                cpe_product = parts[3]
                return product.lower() in cpe_product
        
        # Direct string match
        return product.lower() in cpe
    
    def _calculate_confidence(
        self,
        vuln: Dict,
        service: Dict
    ) -> float:
        """Calculate match confidence."""
        confidence = 0.5
        
        if service.get("version"):
            confidence += 0.2
        
        # Check description
        desc = vuln.get("description", "").lower()
        if service.get("product", "").lower() in desc:
            confidence += 0.1
        
        return min(1.0, round(confidence, 2))
    
    def _generate_evidence(
        self,
        vuln: Dict,
        service: Dict
    ) -> str:
        """Generate match evidence string."""
        parts = [
            f"Service: {service.get('product', 'unknown')}",
            f"Port: {service.get('port', 'unknown')}"
        ]
        
        if service.get("version"):
            parts.append(f"Version: {service['version']}")
        
        return "; ".join(parts)
