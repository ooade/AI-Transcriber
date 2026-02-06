"""Add title column to transcriptions table

Revision ID: add_title_to_transcriptions
Revises: remove_model_version
Create Date: 2026-02-04 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_title_to_transcriptions'
down_revision: Union[str, Sequence[str], None] = 'remove_model_version'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add title column to transcriptions table."""
    try:
        op.add_column('transcriptions', sa.Column('title', sa.String(), nullable=True))
    except Exception:
        # If column already exists, continue
        pass


def downgrade() -> None:
    """Remove title column from transcriptions table."""
    try:
        op.drop_column('transcriptions', 'title')
    except Exception:
        # If column doesn't exist, continue
        pass
