# NetScope Database Migrations

"""
Alembic migration support for database schema changes.
"""

from alembic import command
from alembic.config import Config
import os


def get_alembic_config() -> Config:
    """Get Alembic configuration object."""
    # Search for alembic.ini in multiple locations
    search_paths = [
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini"),  # app/database/
        os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"),  # backend/
        os.path.join(os.getcwd(), "alembic.ini"),  # current directory
    ]
    
    alembic_path = None
    for path in search_paths:
        if os.path.exists(path):
            alembic_path = path
            break
    
    if not alembic_path:
        raise FileNotFoundError("alembic.ini not found. Please create it in the backend directory.")
    
    config = Config(alembic_path)
    return config


def upgrade(revision: str = "head") -> None:
    """Upgrade to a specific revision."""
    config = get_alembic_config()
    command.upgrade(config, revision)


def downgrade(revision: str = "-1") -> None:
    """Downgrade by one revision (default) or to specific."""
    config = get_alembic_config()
    command.downgrade(config, revision)


def revision(message: str = None, autogenerate: bool = False) -> str:
    """Create a new migration revision."""
    config = get_alembic_config()
    revision_id = command.revision(config, message=message, autogenerate=autogenerate)
    return revision_id


def current() -> str:
    """Show the current revision."""
    config = get_alembic_config()
    return command.current(config)


def history() -> str:
    """Show the revision history."""
    config = get_alembic_config()
    return command.history(config)
