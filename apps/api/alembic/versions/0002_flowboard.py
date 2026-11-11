"""flowboard: pipelines table + generation chain columns

Revision ID: 0002_flowboard
Revises: 0001_initial
Create Date: 2026-11-11

0001 uses metadata.create_all which never alters existing tables, so this delta
performs explicit ops (safe to re-run only via alembic's revision bookkeeping).
"""
revision = "0002_flowboard"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("name", sa.String(80), nullable=False, server_default=""),
        sa.Column("spec", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="running"),
        sa.Column("error_message", sa.String(400), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pipelines_user_id", "pipelines", ["user_id"])
    op.create_index("ix_pipelines_status", "pipelines", ["status"])
    op.add_column("generations", sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id"), nullable=True))
    op.add_column("generations", sa.Column("pipeline_step", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_gen_pipeline", "generations", ["pipeline_id"])


def downgrade() -> None:
    op.drop_index("ix_gen_pipeline", table_name="generations")
    op.drop_column("generations", "pipeline_step")
    op.drop_column("generations", "pipeline_id")
    op.drop_index("ix_pipelines_status", table_name="pipelines")
    op.drop_index("ix_pipelines_user_id", table_name="pipelines")
    op.drop_table("pipelines")
