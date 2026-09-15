"""activity feed: club-wide activity events

Revision ID: a1b2c3d4e5f6
Revises: 40486c1afd58
Create Date: 2026-09-15 10:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '40486c1afd58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('activity_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('actor_name', sa.String(length=120), nullable=False),
    sa.Column('icon', sa.String(length=8), nullable=False),
    sa.Column('text', sa.String(length=240), nullable=False),
    sa.Column('link', sa.String(length=160), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('activity_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_activity_events_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_activity_events_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_activity_events_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('activity_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_activity_events_created_at'))
        batch_op.drop_index(batch_op.f('ix_activity_events_actor_id'))
        batch_op.drop_index(batch_op.f('ix_activity_events_kind'))

    op.drop_table('activity_events')
