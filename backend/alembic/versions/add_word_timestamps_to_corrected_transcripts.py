"""Add word_timestamps column to corrected_transcripts table.

Revision ID: add_word_timestamps_to_corrected
Revises: add_speakers_v1
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


revision = "add_word_timestamps_to_corrected"
down_revision = "add_speakers_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "corrected_transcripts",
        sa.Column("word_timestamps", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("corrected_transcripts", "word_timestamps")
