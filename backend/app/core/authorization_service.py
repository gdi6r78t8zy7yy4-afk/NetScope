# NetScope Authorization Service

"""
Authorization service for scan scope enforcement.
"""

import os
from typing import List, Dict, Optional, Set
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class AuthorizationService:
    """
    Manages scan target authorization.
    
    Features:
    - Load authorized targets from configuration files
    - Support multiple target formats (single IP, CIDR, ranges)
    - Audit logging for authorization decisions
    - Support for test vs production modes
    """
    
    DEFAULT_AUTHORIZED_SCOPES = [
        "127.0.0.0/8",      # Localhost
        "::1/128",          # IPv6 localhost
    ]
    
    ENV_VAR_SCOPES = "NETSCOPE_AUTHORIZED_TARGETS"
    CONFIG_FILE_SCOPES = "authorized_scopes.json"
    
    def __init__(
        self,
        authorized_scopes: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize authorization service.
        
        Args:
            authorized_scopes: List of authorized CIDR ranges
            strict_mode: If True, reject targets not explicitly in scope
        """
        self.authorized_scopes = authorized_scopes or []
        self.strict_mode = strict_mode
        self._load_from_env()
        
        # Load from config file if it exists
        self._load_from_config_file()
        
        logger.info(
            "Authorization service initialized",
            scope_count=len(self.authorized_scopes),
            strict_mode=strict_mode
        )
    
    def _load_from_env(self) -> None:
        """Load authorized scopes from environment variable."""
        env_value = os.environ.get(self.ENV_VAR_SCOPES)
        if env_value:
            scopes = [s.strip() for s in env_value.split(",")]
            self.authorized_scopes.extend(scopes)
            logger.info("Loaded scopes from environment", scope_count=len(scopes))
    
    def _load_from_config_file(self) -> None:
        """Load authorized scopes from configuration file."""
        config_path = Path.cwd() / self.CONFIG_FILE_SCOPES
        if not config_path.exists():
            # Try backend directory
            config_path = Path.cwd() / "backend" / self.CONFIG_FILE_SCOPES
        
        if config_path.exists():
            try:
                import json
                with open(config_path, "r") as f:
                    config = json.load(f)
                    scopes = config.get("authorized_scopes", [])
                    self.authorized_scopes.extend(scopes)
                # Deduplicate scopes after loading from config file
                self.authorized_scopes = list(set(self.authorized_scopes))
                logger.info(
                    "Loaded scopes from config file",
                    path=str(config_path),
                    scope_count=len(self.authorized_scopes)
                )
            except Exception as e:
                logger.warning("Failed to load config file", path=str(config_path), error=str(e))
    
    def get_authorized_scopes(self) -> List[str]:
        """Return list of authorized CIDR ranges."""
        return self.authorized_scopes.copy()
    
    def is_authorized(self, target: str) -> Dict[str, any]:
        """
        Check if a target is authorized for scanning.
        
        Args:
            target: Target IP or CIDR to check
            
        Returns:
            Dict with 'authorized' boolean and 'reason' string
        """
        from app.core.target_validator import TargetValidator
        
        validator = TargetValidator(self.authorized_scopes)
        return validator.is_authorized(target)
    
    def validate_target(
        self,
        target: str,
        require_authorized: bool = True
    ) -> Dict[str, any]:
        """
        Validate a target for scanning.
        
        Args:
            target: Target to validate
            require_authorized: Whether authorization is required
            
        Returns:
            Dict with validation results
        """
        from app.core.target_validator import TargetValidator
        
        validator = TargetValidator(self.authorized_scopes)
        return validator.validate_target(target, require_authorized)
    
    def validate_targets(
        self,
        targets: List[str],
        require_authorized: bool = True
    ) -> Dict[str, any]:
        """
        Validate multiple targets.
        
        Args:
            targets: List of target strings
            require_authorized: Whether authorization is required
            
        Returns:
            Dict with validation results
        """
        from app.core.target_validator import TargetValidator
        
        validator = TargetValidator(self.authorized_scopes)
        return validator.validate_targets(targets, require_authorized)
    
    def audit_log(
        self,
        action: str,
        target: str,
        authorized: bool,
        details: Optional[Dict] = None
    ) -> None:
        """
        Log an authorization decision.
        
        Args:
            action: Action performed (scan, discovery, etc.)
            target: Target that was authorized
            authorized: Whether authorization was granted
            details: Additional context
        """
        log_entry = {
            "action": action,
            "target": target,
            "authorized": authorized,
        }
        if details:
            log_entry.update(details)
        
        logger.info("Authorization audit", **log_entry)
    
    def get_unauthorized_targets(
        self,
        targets: List[str],
        require_authorized: bool = True
    ) -> Dict[str, any]:
        """
        Find unauthorized targets.
        
        Args:
            targets: List of targets to check
            require_authorized: Whether authorization is required
            
        Returns:
            Dict with authorized and unauthorized targets
        """
        results = self.validate_targets(targets, require_authorized)
        
        authorized = [
            r["target"] for r in results["results"]
            if r["valid"]
        ]
        unauthorized = [
            r["target"] for r in results["results"]
            if not r["valid"]
        ]
        
        return {
            "total": len(targets),
            "authorized": authorized,
            "unauthorized": unauthorized,
            "invalid_count": len(unauthorized),
        }
    
    def get_valid_targets(
        self,
        targets: List[str]
    ) -> List[str]:
        """
        Get list of valid (authorized) targets.
        
        Args:
            targets: List of target strings
            
        Returns:
            List of valid targets
        """
        results = self.validate_targets(targets)
        return [
            r["target"] for r in results["results"]
            if r["valid"]
        ]


# Singleton instance
_authorization_service: Optional[AuthorizationService] = None


def get_authorization_service(
    authorized_scopes: Optional[List[str]] = None,
    strict_mode: bool = False
) -> AuthorizationService:
    """
    Get the authorization service instance.
    
    Args:
        authorized_scopes: Optional list of authorized CIDR ranges
        strict_mode: If True, reject targets not explicitly in scope
        
    Returns:
        AuthorizationService instance
    """
    global _authorization_service
    
    if authorized_scopes is not None or strict_mode:
        # Create new instance with custom settings
        _authorization_service = AuthorizationService(
            authorized_scopes=authorized_scopes,
            strict_mode=strict_mode
        )
    elif _authorization_service is None:
        # Create default instance
        _authorization_service = AuthorizationService()
    
    return _authorization_service
