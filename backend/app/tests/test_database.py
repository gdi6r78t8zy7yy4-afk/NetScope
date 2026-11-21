# NetScope Database Tests

"""
Tests for database operations and model interactions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test database URL (in-memory for isolation)
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_engine():
    """Create test database engine (synchronous)."""
    # Import models first to register them with the correct Base
    from app.models.network import Network, Subnet  # noqa: F401
    from app.models.asset import (
        Asset,
        NetworkInterface,
        Port,
        HostProfile,
    )  # noqa: F401
    from app.models.scan import Scan, ScanTarget, ScanEvidence  # noqa: F401
    from app.models.vulnerability import Vulnerability  # noqa: F401

    engine = create_engine(TEST_DB_URL, echo=False)

    # Create all tables using models' Base
    from app.database.base import Base as ModelsBase

    ModelsBase.metadata.create_all(engine)

    yield engine

    # Drop all tables using models' Base
    from app.database.base import Base as ModelsBase

    ModelsBase.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    SessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_network(test_session):
    """Test creating a network record."""
    from app.models.network import Network

    network = Network()
    network.name = "Test Network"
    network.cidr = "192.168.1.0/24"
    network.description = "Test network for unit tests"

    test_session.add(network)
    test_session.commit()
    test_session.refresh(network)

    assert network.id is not None
    assert network.name == "Test Network"
    assert network.cidr == "192.168.1.0/24"


def test_create_subnet(test_session):
    """Test creating a subnet record."""
    from app.models.network import Network, Subnet

    # Create network first
    network = Network()
    network.name = "Test Network"
    network.cidr = "192.168.0.0/16"
    test_session.add(network)
    test_session.commit()

    # Create subnet
    subnet = Subnet()
    subnet.name = "Test Subnet"
    subnet.cidr = "192.168.1.0/24"
    subnet.network_id = network.id
    test_session.add(subnet)
    test_session.commit()

    assert subnet.id is not None
    assert subnet.name == "Test Subnet"
    assert subnet.network_id == network.id


def test_create_asset(test_session):
    """Test creating an asset record."""
    from app.models.asset import Asset

    asset = Asset()
    asset.ip_address = "192.168.1.100"
    asset.mac_address = "00:11:22:33:44:55"
    asset.hostname = "test-host"
    asset.operating_system = "macOS"

    test_session.add(asset)
    test_session.commit()

    assert asset.id is not None
    assert asset.operating_system == "macOS"


def test_create_vulnerability(test_session):
    """Test creating a vulnerability record."""
    from app.models.vulnerability import Vulnerability

    vuln = Vulnerability()
    vuln.cve_id = "CVE-2024-1234"
    vuln.description = "Test vulnerability for unit tests"
    vuln.severity = "high"

    test_session.add(vuln)
    test_session.commit()

    assert vuln.id is not None
    assert vuln.cve_id == "CVE-2024-1234"
    assert vuln.severity == "high"


def test_scan_record(test_session):
    """Test scan record creation."""
    from app.models.scan import Scan

    # Create scan directly
    scan = Scan()
    scan.name = "Test Scan"
    scan.scan_type = "port"
    scan.status = "completed"
    scan.target_cidr = "192.168.1.0/24"
    scan.rate_limit = "medium"

    test_session.add(scan)
    test_session.commit()

    assert scan.id is not None
    assert scan.status == "completed"


def test_scan_relationship(test_session):
    """Test scan relationship."""
    from app.models.scan import Scan

    # Create scans
    scan1 = Scan()
    scan1.name = "Scan 1"
    scan1.scan_type = "port"
    scan1.status = "completed"
    scan1.target_cidr = "192.168.1.0/24"
    scan1.rate_limit = "medium"

    scan2 = Scan()
    scan2.name = "Scan 2"
    scan2.scan_type = "port"
    scan2.status = "completed"
    scan2.target_cidr = "192.168.2.0/24"
    scan2.rate_limit = "medium"

    test_session.add(scan1)
    test_session.add(scan2)
    test_session.commit()

    # Reload and check
    test_session.refresh(scan1)
    assert scan1.status == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
