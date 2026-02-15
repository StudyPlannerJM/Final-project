"""Update StudyPlan model with time_value and time_unit fields

Revision ID: f5a8b9c7d2e1
Revises: d12431e3e729
Create Date: 2026-02-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5a8b9c7d2e1'
down_revision = 'd12431e3e729'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns
    with op.batch_alter_table('study_plan', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_value', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('time_unit', sa.String(length=20), nullable=True))
    
    # Update existing rows with default values (convert days_until_exam to time_value with 'days' unit)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE study_plan 
        SET time_value = days_until_exam, 
            time_unit = 'days'
        WHERE time_value IS NULL
    """))
    
    # Make the new columns non-nullable
    with op.batch_alter_table('study_plan', schema=None) as batch_op:
        batch_op.alter_column('time_value', nullable=False)
        batch_op.alter_column('time_unit', nullable=False)
        # Drop old columns
        batch_op.drop_column('hours_per_day')
        batch_op.drop_column('days_until_exam')


def downgrade():
    # Reverse the migration
    with op.batch_alter_table('study_plan', schema=None) as batch_op:
        batch_op.add_column(sa.Column('days_until_exam', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hours_per_day', sa.Float(), nullable=True))
    
    # Restore data (convert time_value back to days_until_exam)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE study_plan 
        SET days_until_exam = CASE 
            WHEN time_unit = 'days' THEN time_value
            WHEN time_unit = 'weeks' THEN time_value * 7
            WHEN time_unit = 'months' THEN time_value * 30
            ELSE time_value
        END,
        hours_per_day = 3.0
        WHERE days_until_exam IS NULL
    """))
    
    with op.batch_alter_table('study_plan', schema=None) as batch_op:
        batch_op.alter_column('days_until_exam', nullable=False)
        batch_op.alter_column('hours_per_day', nullable=False)
        batch_op.drop_column('time_unit')
        batch_op.drop_column('time_value')
