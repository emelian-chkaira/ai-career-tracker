"""Crawl memory per employer: when its internship pages were last read (weekly pass), and what earlier scans learned
(dead links, real internship pages, fruitless ATS guesses) so each scan skips work the last one already did

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("student_scan_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("scan_memory", JSONB, nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("companies", "scan_memory")
    op.drop_column("companies", "student_scan_at")
