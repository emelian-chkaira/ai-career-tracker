"""CV Studio library: several CVs and cover letters per account, and which CV a job score used

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("user_docs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("data_enc", sa.Text, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("job_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("job_scores", sa.Column("cv_name", sa.String(120), nullable=True))


def downgrade():
    op.drop_column("job_scores", "cv_name")
    op.drop_table("user_docs")
