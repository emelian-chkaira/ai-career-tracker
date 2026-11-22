"""Sector and country on jobs/companies, per-user CV Studio drafts

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("sector", sa.String(24), nullable=False, server_default="other"))
    op.add_column("jobs", sa.Column("country", sa.String(2), nullable=False, server_default="NL"))
    op.add_column("companies", sa.Column("country", sa.String(2), nullable=False, server_default="NL"))
    op.create_index("ix_jobs_sector", "jobs", ["sector"]); op.create_index("ix_jobs_country", "jobs", ["country"]); op.create_index("ix_companies_country", "companies", ["country"])
    op.create_table("user_cv_drafts",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data_enc", sa.Text, nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    # classify what is already stored (title rules only, a few thousand rows)
    from app.crawler import sectors
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, title, location FROM jobs")).all()
    for i in range(0, len(rows), 1000):
        chunk = [dict(id=r[0], s=(s := sectors.classify(r[1])), cat=sectors.category_of(s), c=sectors.country_of(r[2])) for r in rows[i:i + 1000]]
        if chunk: bind.execute(sa.text("UPDATE jobs SET sector = :s, country = :c, category = :cat WHERE id = :id"), chunk)


def downgrade():
    op.drop_table("user_cv_drafts")
    op.drop_index("ix_companies_country", "companies"); op.drop_index("ix_jobs_country", "jobs"); op.drop_index("ix_jobs_sector", "jobs")
    op.drop_column("companies", "country"); op.drop_column("jobs", "country"); op.drop_column("jobs", "sector")
