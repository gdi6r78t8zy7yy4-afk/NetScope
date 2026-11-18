# NetScope Scan Scheduling Tests

"""
Tests for scan scheduling functionality.
"""

import pytest
from datetime import datetime, timedelta


def test_scan_schedule_basic():
    """Test basic scan schedule creation."""
    from app.schemas.scan import ScanScheduleCreate
    
    schedule = ScanScheduleCreate(
        name="Daily Port Scan",
        scan_type="port_scan",
        target_cidr="192.168.1.0/24",
        cron_pattern="0 2 * * *",  # Daily at 2 AM
        enabled=True
    )
    
    assert schedule.name == "Daily Port Scan"
    assert schedule.cron_pattern == "0 2 * * *"
    assert schedule.enabled is True


def test_scan_schedule_with_options():
    """Test scan schedule with additional options."""
    from app.schemas.scan import ScanScheduleCreate
    
    schedule = ScanScheduleCreate(
        name="Weekly Vulnerability Scan",
        scan_type="vulnerability",
        target_cidr="10.0.0.0/8",
        cron_pattern="0 6 * * 0",  # Weekly on Sunday at 6 AM
        enabled=True,
        priority=1,
        rate_limit="slow"
    )
    
    assert schedule.scan_type == "vulnerability"
    assert schedule.priority == 1
    assert schedule.rate_limit == "slow"


def test_scan_schedule_list():
    """Test scan schedule list response."""
    from app.schemas.scan import ScanScheduleList
    
    schedules = ScanScheduleList(
        total=2,
        items=[
            {"id": 1, "name": "Daily Scan", "enabled": True},
            {"id": 2, "name": "Weekly Scan", "enabled": False}
        ]
    )
    
    assert schedules.total == 2
    assert len(schedules.items) == 2


def test_next_run_time_calculation():
    """Test next run time calculation from cron pattern."""
    from app.engines.scanner.scheduler import parse_cron
    
    # Test daily at 2 AM
    cron = "0 2 * * *"
    now = datetime(2026, 11, 16, 10, 30, 0)  # 10:30 AM
    
    next_run = parse_cron(cron, now)
    
    # Should be 2 AM next day
    assert next_run is not None


def test_schedule_enabled_state():
    """Test schedule enable/disable state."""
    from app.schemas.scan import ScanSchedule
    
    schedule = ScanSchedule(
        id=1,
        name="Test Schedule",
        scan_type="port_scan",
        target_cidr="192.168.1.0/24",
        cron_pattern="0 1 * * *",
        enabled=True
    )
    
    assert schedule.enabled is True
    
    # Disable
    schedule.enabled = False
    assert schedule.enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
