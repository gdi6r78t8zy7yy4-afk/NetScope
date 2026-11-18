# NetScope Service Correlator

"""
Service-level vulnerability correlation.
"""

from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ServiceCorrelator:
    """
    Correlate vulnerabilities with individual services.
    """
    
    def __init__(self):
        self.logger = logger.bind(correlator="service")
    
    async def correlate_service(
        self,
        service: Dict,
        vuln_database: List[Dict]
    ) -> List[Dict]:
        """
        Correlate vulnerabilities for a single service.
        
        Args:
            service: Service information
            vuln_database: Vulnerability database
            
        Returns:
            List of potential vulnerabilities
        """
        self.logger.info(
            "Correlating service",
            port=service.get("port"),
            product=service.get("product")
        )
        
        findings = []
        
        for vuln in vuln_database:
            match = self._match_vuln_to_service(vuln, service)
            
            if match:
                findings.append(match)
        
        return findings
    
    def _match_vuln_to_service(
        self,
        vuln: Dict,
        service: Dict
    ) -> Optional[Dict]:
        """Match vulnerability to service."""
        cpe = vuln.get("cpe_match", "").lower()
        product = service.get("product", "").lower()
        
        if not cpe or not product:
            return None
        
        # Check CPE product field
        if "cpe:" in cpe:
            parts = cpe.split(":")
            if len(parts) >= 4:
                vuln_product = parts[3]
                
                if product in vuln_product or vuln_product in product:
                    return self._create_finding(vuln, service)
        
        # Fallback to description matching
        desc = vuln.get("description", "").lower()
        if product in desc:
            return self._create_finding(vuln, service)
        
        return None
    
    def _create_finding(
        self,
        vuln: Dict,
        service: Dict
    ) -> Dict:
        """Create a vulnerability finding."""
        return {
            "cve_id": vuln.get("cve_id"),
            "confidence": self._calculate_confidence(vuln, service),
            "cvss_score": vuln.get("cvss_score"),
            "severity": vuln.get("severity"),
            "evidence": self._generate_evidence(vuln, service)
        }
    
    def _calculate_confidence(
        self,
        vuln: Dict,
        service: Dict
    ) -> float:
        """Calculate confidence score."""
        confidence = 0.5
        
        # Version check
        if service.get("version"):
            confidence += 0.25
        
        # Description match strength
        desc = vuln.get("description", "").lower()
        product = service.get("product", "").lower()
        
        if desc.count(product) > 1:
            confidence += 0.2
        
        return min(1.0, round(confidence, 2))
    
    def _generate_evidence(
        self,
        vuln: Dict,
        service: Dict
    ) -> str:
        """Generate evidence string."""
        parts = [
            f"Port: {service.get('port', 'unknown')}",
            f"Product: {service.get('product', 'unknown')}"
        ]
        
        if service.get("version"):
            parts.append(f"Version: {service['version']}")
        
        return "; ".join(parts)
