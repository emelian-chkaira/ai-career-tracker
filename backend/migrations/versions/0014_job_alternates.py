"""One role, one job: other locations / links of the same role live in jobs.alternates

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("alternates", JSONB, nullable=False, server_default="[]"))
    # existing duplicates are folded by maintenance_service.collapse_duplicates (run by the worker daily, or Crawler -> Tasks -> "Merge duplicate jobs")


def downgrade():
    op.drop_column("jobs", "alternates")
