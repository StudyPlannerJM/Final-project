"""Add spaced repetition fields to flashcard and the card_review log

Revision ID: a1c4e7f20b53
Revises: 3f2d9e4c1a7b
Create Date: 2026-11-11 00:00:00.000000

Additive only. Existing flashcards get the defaults, which make them
"new" cards that are due immediately.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c4e7f20b53'
down_revision = '3f2d9e4c1a7b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('flashcard', schema=None) as batch_op:
        batch_op.add_column(sa.Column('due_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('interval_days', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('ease', sa.Float(), nullable=False, server_default='2.5'))
        batch_op.add_column(sa.Column('reps', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('lapses', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('last_reviewed_at', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_flashcard_due_at', ['due_at'], unique=False)

    op.create_table(
        'card_review',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('flashcard_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['flashcard_id'], ['flashcard.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_card_review_user_time', 'card_review', ['user_id', 'reviewed_at'], unique=False)


def downgrade():
    op.drop_index('idx_card_review_user_time', table_name='card_review')
    op.drop_table('card_review')

    with op.batch_alter_table('flashcard', schema=None) as batch_op:
        batch_op.drop_index('ix_flashcard_due_at')
        batch_op.drop_column('last_reviewed_at')
        batch_op.drop_column('lapses')
        batch_op.drop_column('reps')
        batch_op.drop_column('ease')
        batch_op.drop_column('interval_days')
        batch_op.drop_column('due_at')
