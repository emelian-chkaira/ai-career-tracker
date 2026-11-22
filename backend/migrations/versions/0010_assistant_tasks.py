"""per-job assistant messages and job tasks

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("job_chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False), sa.Column("content", sa.Text, nullable=False), sa.Column("model", sa.String(100)),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_job_chat_user_job_at", "job_chat_messages", ["user_id", "job_id", "at"])
    op.create_table("job_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("done_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_job_tasks_user_id", "job_tasks", ["user_id"]); op.create_index("ix_job_tasks_job_id", "job_tasks", ["job_id"])


def downgrade():
    op.drop_table("job_tasks"); op.drop_table("job_chat_messages")
