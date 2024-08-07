"""initial_migration_with_all_changes

Revision ID: initial_migration_with_all_changes
Revises: 
Create Date: 2024-05-23 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'initial_migration_with_all_changes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone')
    )
    op.create_index(op.f('ix_user_name'), 'user', ['name'], unique=True)
    
    op.create_table('exercise_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.Column('left_forearm_innerbody', sa.Integer(), nullable=True),
    sa.Column('left_forearm_outterbody', sa.Integer(), nullable=True),
    sa.Column('right_forearm_innerbody', sa.Integer(), nullable=True),
    sa.Column('right_forearm_outterbody', sa.Integer(), nullable=True),
    sa.Column('diagnosis', sa.Text(), nullable=True),
    sa.Column('exercise_time', sa.Integer(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('exercise_data')
    op.drop_index(op.f('ix_user_name'), table_name='user')
    op.drop_table('user')
    # ### end Alembic commands ###
