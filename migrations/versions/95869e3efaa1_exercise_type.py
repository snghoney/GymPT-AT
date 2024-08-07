"""exercise_type

Revision ID: 95869e3efaa1
Revises: 4af6a8362325
Create Date: 2024-06-26 11:18:34.432221

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95869e3efaa1'
down_revision = '4af6a8362325'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercise_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('exercise_type', sa.String(length=64), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercise_data', schema=None) as batch_op:
        batch_op.drop_column('exercise_type')

    # ### end Alembic commands ###
