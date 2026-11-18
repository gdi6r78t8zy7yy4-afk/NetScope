# NetScope Correlation Engine Package

"""
Vulnerability correlation engines.
"""

from app.engines.correlation.asset_correlator import AssetCorrelator
from app.engines.correlation.service_correlator import ServiceCorrelator

__all__ = [
    "AssetCorrelator",
    "ServiceCorrelator",
]
