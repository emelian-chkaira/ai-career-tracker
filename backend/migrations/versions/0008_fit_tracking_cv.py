"""AI fit scores, stored CV, tracking timeline, tailored CVs

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    for c in (sa.Column('applied_at', TS), sa.Column('follow_up_at', TS), sa.Column('follow_up_note', sa.String(200)), sa.Column('contact', sa.String(200)), sa.Column('offer_details', sa.String(200))):
        op.add_column('user_jobs', c)
    op.create_index('ix_user_jobs_follow_up_at', 'user_jobs', ['follow_up_at'])
    op.create_table('job_events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('job_id', sa.Integer, sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('kind', sa.String(20), nullable=False), sa.Column('title', sa.String(200), nullable=False), sa.Column('body', sa.Text),
        sa.Column('at', TS, server_default=sa.func.now(), nullable=False), sa.Column('meta', pg.JSONB, server_default='{}', nullable=False))
    op.create_index('ix_job_events_user_job_at', 'job_events', ['user_id', 'job_id', 'at'])
    op.create_table('user_cvs',
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('data_enc', sa.Text, nullable=False), sa.Column('text_hash', sa.String(64), nullable=False), sa.Column('updated_at', TS, server_default=sa.func.now(), nullable=False))
    op.create_table('job_scores',
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('job_id', sa.Integer, sa.ForeignKey('jobs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('score', sa.Integer, nullable=False, index=True), sa.Column('verdict', sa.String(16), nullable=False), sa.Column('reason', sa.Text, nullable=False),
        sa.Column('strengths', pg.JSONB, server_default='[]', nullable=False), sa.Column('gaps', pg.JSONB, server_default='[]', nullable=False), sa.Column('flags', pg.JSONB, server_default='[]', nullable=False),
        sa.Column('summary', sa.Text), sa.Column('model', sa.String(100), server_default='', nullable=False), sa.Column('basis_hash', sa.String(64), nullable=False),
        sa.Column('created_at', TS, server_default=sa.func.now(), nullable=False))
    op.create_table('job_cvs',
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('job_id', sa.Integer, sa.ForeignKey('jobs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('data_enc', sa.Text, nullable=False), sa.Column('template', sa.String(20), server_default='classic', nullable=False), sa.Column('report', pg.JSONB, server_default='{}', nullable=False),
        sa.Column('cover_letter', sa.Text), sa.Column('model', sa.String(100), server_default='', nullable=False), sa.Column('updated_at', TS, server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    for t in ('job_cvs', 'job_scores', 'user_cvs', 'job_events'): op.drop_table(t)
    op.drop_index('ix_user_jobs_follow_up_at', 'user_jobs')
    for c in ('offer_details', 'contact', 'follow_up_note', 'follow_up_at', 'applied_at'): op.drop_column('user_jobs', c)
