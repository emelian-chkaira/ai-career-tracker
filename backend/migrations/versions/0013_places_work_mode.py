"""Every country a job names, work mode (on-site / hybrid / remote) and remote scope; company country

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("countries", ARRAY(sa.String(2)), nullable=False, server_default="{}"))
    op.add_column("jobs", sa.Column("work_mode", sa.String(8), nullable=False, server_default="onsite"))
    op.add_column("jobs", sa.Column("remote_scope", sa.String(16)))
    op.create_index("ix_jobs_work_mode", "jobs", ["work_mode"])
    op.execute("CREATE INDEX ix_jobs_countries ON jobs USING gin (countries)")
    from app.crawler import places
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT j.id, j.location, j.title, j.url, c.country FROM jobs j JOIN companies c ON c.id = j.company_id")).all()
    out = []
    for i, loc, title, url, cc in rows:
        p = places.parse(loc, title or "")
        if not p.countries and p.remote_scope in (None, "world") and (loc or "").strip().lower() in ("", "remote"):
            tld = (url or "").split("/")[2].rsplit(".", 1)[-1].lower() if (url or "").count("/") >= 2 else ""
            p.countries = [{"de": "DE", "be": "BE", "fr": "FR", "uk": "GB", "it": "IT", "es": "ES", "pl": "PL", "ae": "AE"}.get(tld, cc or "NL")]; p.remote_scope = None
        out.append(dict(id=i, cs=p.countries, c=p.country or cc or "NL", m=p.work_mode, s=p.remote_scope, r=p.work_mode != "onsite"))
    for k in range(0, len(out), 1000):
        bind.execute(sa.text("UPDATE jobs SET countries = :cs, country = :c, work_mode = :m, remote_scope = :s, remote = :r WHERE id = :id"), out[k:k + 1000])


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_jobs_countries"); op.drop_index("ix_jobs_work_mode", "jobs")
    op.drop_column("jobs", "remote_scope"); op.drop_column("jobs", "work_mode"); op.drop_column("jobs", "countries")
