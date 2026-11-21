"""Initial database schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create assets table
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("device_type", sa.String(length=100), nullable=True),
        sa.Column("operating_system", sa.String(length=255), nullable=True),
        sa.Column("os_version", sa.String(length=100), nullable=True),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column(
            "confidence_level",
            sa.String(length=20),
            server_default="unknown",
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assets_ip_address"), "assets", ["ip_address"], unique=False
    )
    op.create_index(
        op.f("ix_assets_mac_address"), "assets", ["mac_address"], unique=False
    )

    # Create network_interfaces table
    op.create_table(
        "network_interfaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("mac_address", sa.String(length=17), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("interface_type", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_network_interfaces_asset_id"),
        "network_interfaces",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_interfaces_ip_address"),
        "network_interfaces",
        ["ip_address"],
        unique=False,
    )

    # Create ports table
    op.create_table(
        "ports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("port_number", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=10), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=True),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("cpe", sa.Text(), nullable=True),
        sa.Column("banner", sa.Text(), nullable=True),
        sa.Column(
            "detection_confidence",
            sa.String(length=20),
            server_default="medium",
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ports_asset_id"),
        "ports",
        ["asset_id"],
        unique=False)
    op.create_index(
        op.f("ix_ports_port_number"), "ports", ["port_number"], unique=False
    )

    # Create scans table
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("scan_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column(
            "progress",
            sa.Integer(),
            server_default="0",
            nullable=False),
        sa.Column("target_cidr", sa.String(length=100), nullable=False),
        sa.Column(
            "rate_limit", sa.String(length=20), server_default="medium", nullable=True
        ),
        sa.Column("ports", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scans_status"), "scans", ["status"], unique=False)
    op.create_index(
        op.f("ix_scans_scan_type"),
        "scans",
        ["scan_type"],
        unique=False)

    # Create scan_targets table
    op.create_table(
        "scan_targets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("target_ip", sa.String(length=45), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_targets_scan_id"), "scan_targets", ["scan_id"], unique=False
    )

    # Create scan_evidence table
    op.create_table(
        "scan_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("host_ip", sa.String(length=45), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column(
            "confidence", sa.String(length=20), server_default="medium", nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_evidence_scan_id"), "scan_evidence", ["scan_id"], unique=False
    )

    # Create vulnerabilities table
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cve_id", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column(
            "cvss_version", sa.String(length=10), server_default="3.1", nullable=True
        ),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column(
            "is_kev",
            sa.Boolean(),
            server_default="false",
            nullable=False),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column("epss_percentile", sa.Float(), nullable=True),
        sa.Column("cpe", sa.Text(), nullable=True),
        sa.Column("source_data", sa.JSON(), nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index(
        op.f("ix_vulnerabilities_cve_id"), "vulnerabilities", ["cve_id"], unique=False
    )
    op.create_index(
        op.f("ix_vulnerabilities_severity"),
        "vulnerabilities",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vulnerabilities_is_kev"), "vulnerabilities", ["is_kev"], unique=False
    )

    # Create asset_vulnerability table
    op.create_table(
        "asset_vulnerability",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("vulnerability_id", sa.Integer(), nullable=False),
        sa.Column("matching_method", sa.String(length=50), nullable=True),
        sa.Column(
            "match_confidence",
            sa.String(length=20),
            server_default="medium",
            nullable=True,
        ),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column(
            "is_kev",
            sa.Boolean(),
            server_default="false",
            nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column(
            "last_verified_at",
            sa.DateTime(
                timezone=True),
            nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["vulnerability_id"], ["vulnerabilities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_vulnerability_asset_id"),
        "asset_vulnerability",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_vulnerability_vulnerability_id"),
        "asset_vulnerability",
        ["vulnerability_id"],
        unique=False,
    )

    # Create asset_history table
    op.create_table(
        "asset_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("old_data", sa.JSON(), nullable=True),
        sa.Column("new_data", sa.JSON(), nullable=True),
        sa.Column("scan_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_history_asset_id"), "asset_history", ["asset_id"], unique=False
    )
    op.create_index(
        op.f("ix_asset_history_change_type"),
        "asset_history",
        ["change_type"],
        unique=False,
    )

    # Create networks table
    op.create_table(
        "networks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("cidr", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cidr"),
    )
    op.create_index(
        op.f("ix_networks_cidr"),
        "networks",
        ["cidr"],
        unique=False)

    # Create subnets table
    op.create_table(
        "subnets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("network_id", sa.Integer(), nullable=False),
        sa.Column("cidr", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["network_id"],
            ["networks.id"],
            ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subnets_cidr"), "subnets", ["cidr"], unique=False)
    op.create_index(
        op.f("ix_subnets_network_id"), "subnets", ["network_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("subnets")
    op.drop_table("networks")
    op.drop_table("asset_history")
    op.drop_table("asset_vulnerability")
    op.drop_table("vulnerabilities")
    op.drop_table("scan_evidence")
    op.drop_table("scan_targets")
    op.drop_table("scans")
    op.drop_table("ports")
    op.drop_table("network_interfaces")
    op.drop_table("assets")
