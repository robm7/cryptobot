"""test_migration

Revision ID: b84406c62569
Revises: cdebfb10ff6a
Create Date: 2025-05-03 23:35:11.794326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b84406c62569'
down_revision: Union[str, None] = 'cdebfb10ff6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
