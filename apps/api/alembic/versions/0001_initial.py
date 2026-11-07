"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-07
"""
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from alembic import op
from app.core.db import Base
import app.models  # noqa: F401


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
