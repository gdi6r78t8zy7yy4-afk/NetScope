# NetScope Service Detection Package

"""
Service detection engine for identifying services on open ports.
"""

from app.engines.service_detection.detector import ServiceDetector

__all__ = [
    "ServiceDetector",
]
