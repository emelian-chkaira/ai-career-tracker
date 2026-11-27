"""Remember that a posting's own page was read for its date

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("date_checked_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("jobs", "date_checked_at")
