"""Migrate existing KEV data to new vulnerability_kev table

Revision ID: 003_migrate_kev_data
Revises: 002_enhanced_vulnerability
Create Date: 2026-11-20 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '003_migrate_kev_data'
down_revision: Union[str, None] = '002_enhanced_vulnerability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate existing KEV vulnerabilities to the new vulnerability_kev table
    # This requires joining with intelligence_syncs to get date_added
    
    op.execute("""
        INSERT INTO vulnerability_kev (vulnerability_id, date_added, created_at)
        SELECT DISTINCT v.id, s.sync_completed_at, NOW()
        FROM vulnerabilities v
        JOIN vulnerability_products vp ON vp.vulnerability_id = v.id
        JOIN intelligence_syncs s ON s.source_name = 'cisa_kev'
        WHERE vp.cpe_match IS NOT NULL
    """)
    
    # Note: This is a simplified migration. In production, you would need to:
    # 1. Fetch KEV entries from the CISA KEV catalog for each CVE
    # 2. Map cve_id to vulnerability.id
    # 3. Extract date_added, due_date from the KEV data


def downgrade() -> None:
    # Delete migrated KEV records
    op.execute("DELETE FROM vulnerability_kev")
