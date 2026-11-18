# NetScope Database Base Models

"""
Base classes and common database utilities.
"""

from datetime import datetime
from typing import TypeVar, Optional

from sqlalchemy import DateTime, func, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

T = TypeVar("T", bound="BaseModel")


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    pass


class TimestampModel:
    """Mixin class with timestamp columns (not mapped)."""
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


async def init_db(engine: Optional[Engine] = None) -> None:
    """
    Initialize the database by creating all tables.
    
    This should be called once on application startup.
    Uses Alembic for migrations in production, fallback to create_all() for dev.
    
    Args:
        engine: Optional database engine. Uses default if not provided.
    """
    from app.database import engine as default_engine
    from app.models.asset import Asset, NetworkInterface  # noqa: F401
    from app.models.network import Network, Subnet  # noqa: F401
    from app.models.scan import Scan, ScanTarget  # noqa: F401
    from app.models.vulnerability import Vulnerability  # noqa: F401
    
    use_engine = engine or default_engine
    async with use_engine.begin() as conn:
        # For initial setup, create all tables if no migrations exist
        await conn.run_sync(Base.metadata.create_all)
        
        # Mark the initial migration as applied if alembic_version table doesn't exist
        from sqlalchemy import text
        try:
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"
            ))
            await conn.commit()
        except Exception:
            # Table might already exist
            pass


async def drop_db(engine: Optional[Engine] = None) -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    
    Args:
        engine: Optional database engine. Uses default if not provided.
    """
    from app.database import engine as default_engine
    
    use_engine = engine or default_engine
    async with use_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
