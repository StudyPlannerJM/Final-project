"""Add the login_attempt table used to limit password guessing

Revision ID: b7e2c9d41f06
Revises: a1c4e7f20b53
Create Date: 2026-11-11 12:00:00.000000

Additive only.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e2c9d41f06'
down_revision = 'a1c4e7f20b53'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'login_attempt',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_attempt_email', 'login_attempt', ['email'], unique=False)
    op.create_index('ix_login_attempt_ip', 'login_attempt', ['ip'], unique=False)
    op.create_index('ix_login_attempt_attempted_at', 'login_attempt', ['attempted_at'], unique=False)


def downgrade():
    op.drop_index('ix_login_attempt_attempted_at', table_name='login_attempt')
    op.drop_index('ix_login_attempt_ip', table_name='login_attempt')
    op.drop_index('ix_login_attempt_email', table_name='login_attempt')
    op.drop_table('login_attempt')
