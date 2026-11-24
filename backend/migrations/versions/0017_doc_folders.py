"""Folders in the CV Studio library ("" is the default folder)

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_docs", sa.Column("folder", sa.String(60), nullable=False, server_default=""))


def downgrade():
    op.drop_column("user_docs", "folder")
