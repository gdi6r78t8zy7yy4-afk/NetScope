#!/usr/bin/env python3
"""
Add scan tracking fields to assets table.

This script adds the following columns to the assets table:
- last_seen_scan_id: Tracks which scan most recently found this host
- consecutive_absent_count: Counts how many scans the host has been absent

Usage:
    python3 scripts/add_scan_tracking.py
"""

import asyncio
import sys

# Add parent directory to path
sys.path.insert(0, __file__.rsplit('/', 2)[0])

from sqlalchemy import text

from app.database import engine


async def add_scan_tracking_columns():
    """Add scan tracking columns to assets table."""
    print("Adding scan tracking columns to assets table...")
    
    # Try to use sqlite-specific approach first
    is_sqlite = str(engine.url).startswith("sqlite")
    
    async with engine.begin() as conn:
        if is_sqlite:
            # For SQLite, check table info
            result = await conn.execute(text("""
                PRAGMA table_info(assets)
            """))
            columns = [row[1] for row in result.fetchall()]
            
            col1_exists = "last_seen_scan_id" in columns
            col2_exists = "consecutive_absent_count" in columns
            
            if col1_exists and col2_exists:
                print("Columns already exist, skipping...")
                return
            
            if not col1_exists:
                print("  - Adding last_seen_scan_id column...")
                await conn.execute(text("""
                    ALTER TABLE assets ADD COLUMN last_seen_scan_id INTEGER
                """))
            
            if not col2_exists:
                print("  - Adding consecutive_absent_count column...")
                await conn.execute(text("""
                    ALTER TABLE assets ADD COLUMN consecutive_absent_count INTEGER DEFAULT 0
                """))
        else:
            # For PostgreSQL, use information_schema
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'assets' 
                AND column_name IN ('last_seen_scan_id', 'consecutive_absent_count')
            """))
            existing_cols = [row[0] for row in result.fetchall()]
            
            if "last_seen_scan_id" not in existing_cols:
                print("  - Adding last_seen_scan_id column...")
                await conn.execute(text("""
                    ALTER TABLE assets 
                    ADD COLUMN last_seen_scan_id INTEGER
                """))
            
            if "consecutive_absent_count" not in existing_cols:
                print("  - Adding consecutive_absent_count column...")
                await conn.execute(text("""
                    ALTER TABLE assets 
                    ADD COLUMN consecutive_absent_count INTEGER DEFAULT 0
                """))
        
        await conn.commit()
    
    print("Done! Scan tracking columns added successfully.")


if __name__ == "__main__":
    asyncio.run(add_scan_tracking_columns())
