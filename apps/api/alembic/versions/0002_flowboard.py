"""flowboard: pipelines table + generation chain columns

Revision ID: 0002_flowboard
Revises: 0001_initial
Create Date: 2026-11-11

0001 uses metadata.create_all, which already includes the flowboard model on a
fresh database. So every op here is guarded by an inspector check: this delta
only alters databases created BEFORE the flowboard model existed.
"""
revision = "0002_flowboard"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "pipelines" not in insp.get_table_names():
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

    gen_cols = {c["name"] for c in insp.get_columns("generations")}
    if "pipeline_id" not in gen_cols:
        op.add_column("generations", sa.Column("pipeline_id", sa.String(36),
                                               sa.ForeignKey("pipelines.id"), nullable=True))
    if "pipeline_step" not in gen_cols:
        op.add_column("generations", sa.Column("pipeline_step", sa.Integer(),
                                               nullable=False, server_default="0"))
    # index creation is separately guarded (create_all names it differently)
    existing_idx = {i["name"] for i in insp.get_indexes("generations")}
    if "ix_gen_pipeline" not in existing_idx:
        op.create_index("ix_gen_pipeline", "generations", ["pipeline_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_idx = {i["name"] for i in insp.get_indexes("generations")}
    if "ix_gen_pipeline" in existing_idx:
        op.drop_index("ix_gen_pipeline", table_name="generations")
    gen_cols = {c["name"] for c in insp.get_columns("generations")}
    if "pipeline_step" in gen_cols:
        op.drop_column("generations", "pipeline_step")
    if "pipeline_id" in gen_cols:
        op.drop_column("generations", "pipeline_id")
    if "pipelines" in insp.get_table_names():
        op.drop_table("pipelines")
