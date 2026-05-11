"""Create match_email_sends table

Revision ID: abcd1234
Revises: 9cc0de7c2645
Create Date: 2025-10-05 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abcd1234'
down_revision = '9cc0de7c2645'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'match_email_sends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('recipient_email', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['cycle_id'], ['matching_cycles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cycle_id', 'recipient_email', name='uq_match_email_send_cycle_recipient'),
    )
    op.create_index('idx_match_email_sends_cycle_pending', 'match_email_sends', ['cycle_id'], unique=False, postgresql_where=sa.text('sent_at IS NULL'))


def downgrade():
    op.drop_index('idx_match_email_sends_cycle_pending', table_name='match_email_sends')
    op.drop_table('match_email_sends')


