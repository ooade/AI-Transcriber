"""Add speaker and transcription_segments tables.

Revision ID: add_speakers_v1
Revises: 13dab08d6c6b
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


revision = "add_speakers_v1"
down_revision = "13dab08d6c6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create speakers table
    op.create_table(
        "speakers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("transcription_id", sa.String(), nullable=False),
        sa.Column("speaker_label", sa.String(), nullable=True),
        sa.Column("speaker_name", sa.String(), nullable=True),
        sa.Column("total_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("segment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["transcription_id"], ["transcriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speakers_transcription_id", "speakers", ["transcription_id"])

    # Create transcription_segments table
    op.create_table(
        "transcription_segments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("transcription_id", sa.String(), nullable=False),
        sa.Column("speaker_id", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["speaker_id"], ["speakers.id"]),
        sa.ForeignKeyConstraint(["transcription_id"], ["transcriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_segments_transcription_id", "transcription_segments", ["transcription_id"])
    op.create_index("ix_segments_speaker_id", "transcription_segments", ["speaker_id"])


def downgrade() -> None:
    op.drop_index("ix_segments_speaker_id", "transcription_segments")
    op.drop_index("ix_segments_transcription_id", "transcription_segments")
    op.drop_table("transcription_segments")
    op.drop_index("ix_speakers_transcription_id", "speakers")
    op.drop_table("speakers")
