"""add customer type to users

Revision ID: 67489ede1f07
Revises: 861016afbeec
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '67489ede1f07'
down_revision: Union[str, Sequence[str], None] = '861016afbeec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'customer_type',
            sa.String(length=50),
            nullable=False,
            server_default='household'
        )
    )

    op.alter_column(
        'users',
        'customer_type',
        server_default=None
    )


def downgrade() -> None:
    op.drop_column('users', 'customer_type')