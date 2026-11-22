"""per-task models and writing style for the AI settings

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_ai_settings", sa.Column("task_models", postgresql.JSONB, nullable=False, server_default="{}"))
    op.add_column("user_ai_settings", sa.Column("style", postgresql.JSONB, nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("user_ai_settings", "style")
    op.drop_column("user_ai_settings", "task_models")
