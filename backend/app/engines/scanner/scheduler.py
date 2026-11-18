# NetScope Scan Scheduler

"""
Scan scheduling functionality with cron-like patterns.
"""

import re
from datetime import datetime, timedelta


class ScheduleParser:
    """
    Parse cron-like scheduling patterns.
    
    Supports simplified cron format:
    minute hour day month weekday
    
    Special values:
    - * = all valid values
    - /n = every n units
    - , = list separator
    
    Examples:
    - "0 2 * * *"  # Daily at 2 AM
    - "*/15 * * * *"  # Every 15 minutes
    - "0 6 * * 0"  # Weekly on Sunday at 6 AM
    - "0 9 1 * *"  # Monthly on 1st at 9 AM
    """
    
    def __init__(self, cron_pattern: str):
        self.cron_pattern = cron_pattern
        self.parse()
    
    def parse(self) -> dict:
        """Parse the cron pattern into components."""
        parts = self.cron_pattern.split()
        
        if len(parts) != 5:
            raise ValueError("Cron pattern must have exactly 5 fields")
        
        self.minute, self.hour, self.day, self.month, self.weekday = parts
        
        return {
            "minute": self.parse_field(self.minute, 0, 59),
            "hour": self.parse_field(self.hour, 0, 23),
            "day": self.parse_field(self.day, 1, 31),
            "month": self.parse_field(self.month, 1, 12),
            "weekday": self.parse_field(self.weekday, 0, 6)
        }
    
    def parse_field(self, field: str, min_val: int, max_val: int) -> list:
        """Parse a single cron field."""
        values = []
        
        if field == "*":
            return list(range(min_val, max_val + 1))
        
        # Handle step values (*/n)
        if field.startswith("*/"):
            step = int(field[2:])
            return list(range(min_val, max_val + 1, step))
        
        # Handle ranges (n-m)
        if "-" in field:
            start, end = map(int, field.split("-"))
            return list(range(start, end + 1))
        
        # Handle lists (n,m,o)
        if "," in field:
            return [int(x) for x in field.split(",")]
        
        # Single value
        try:
            val = int(field)
            if min_val <= val <= max_val:
                return [val]
            else:
                raise ValueError(f"Value {val} out of range [{min_val}-{max_val}]")
        except ValueError:
            raise ValueError(f"Invalid cron field: {field}")
    
    def get_next_run(self, from_time: datetime = None) -> datetime:
        """
        Calculate the next run time.
        
        Args:
            from_time: Reference time (default: now)
            
        Returns:
            Next run datetime
        """
        if from_time is None:
            from_time = datetime.now()
        
        # Start from the next minute
        check_time = from_time + timedelta(minutes=1)
        
        # Try up to 366 days ahead
        max_iterations = 366 * 24 * 60
        
        for _ in range(max_iterations):
            if self._matches(check_time):
                return check_time
            check_time += timedelta(minutes=1)
        
        raise ValueError("Could not find next run time within 366 days")
    
    def _matches(self, dt: datetime) -> bool:
        """Check if a datetime matches the schedule."""
        minute = self._match_field(dt.minute, self.parse_field(self.minute, 0, 59))
        hour = self._match_field(dt.hour, self.parse_field(self.hour, 0, 23))
        day = self._match_field(dt.day, self.parse_field(self.day, 1, 31))
        month = self._match_field(dt.month, self.parse_field(self.month, 1, 12))
        weekday = self._match_field(dt.weekday(), self.parse_field(self.weekday, 0, 6))
        
        return minute and hour and day and month and weekday
    
    def _match_field(self, value: int, valid_values: list) -> bool:
        """Check if a value matches the cron field."""
        return value in valid_values


def parse_cron(cron_pattern: str, from_time: datetime = None) -> datetime:
    """
    Parse a cron pattern and return the next run time.
    
    Args:
        cron_pattern: Cron expression
        from_time: Reference time (default: now)
        
    Returns:
        Next run datetime or None if invalid
    """
    try:
        parser = ScheduleParser(cron_pattern)
        return parser.get_next_run(from_time)
    except (ValueError, AttributeError):
        return None


def create_schedule(schedule_data: dict) -> dict:
    """
    Create a scan schedule from data.
    
    Args:
        schedule_data: Schedule configuration
        
    Returns:
        Schedule dictionary
    """
    cron_pattern = schedule_data.get("cron_pattern", "0 * * * *")
    enabled = schedule_data.get("enabled", True)
    
    return {
        "name": schedule_data.get("name", "Untitled Schedule"),
        "cron_pattern": cron_pattern,
        "enabled": enabled,
        "scan_type": schedule_data.get("scan_type", "port_scan"),
        "target_cidr": schedule_data.get("target_cidr", "192.168.0.0/16"),
        "rate_limit": schedule_data.get("rate_limit", "medium")
    }
