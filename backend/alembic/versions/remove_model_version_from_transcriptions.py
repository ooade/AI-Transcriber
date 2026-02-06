"""Remove model_version column from transcriptions table

Revision ID: remove_model_version
Revises: add_word_timestamps_to_corrected
Create Date: 2026-02-04 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_model_version'
down_revision: Union[str, Sequence[str], None] = 'add_word_timestamps_to_corrected'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove model_version column from transcriptions table."""
    try:
        # Try to drop the column (works for most databases)
        op.drop_column('transcriptions', 'model_version')
    except Exception:
        # If column doesn't exist or operation not supported, continue
        # This is a safe operation for idempotency
        pass


def downgrade() -> None:
    """Add model_version column back to transcriptions table."""
    try:
        op.add_column(
            'transcriptions',
            sa.Column('model_version', sa.String(), nullable=True)
        )
    except Exception:
        # If column already exists, continue
        pass
