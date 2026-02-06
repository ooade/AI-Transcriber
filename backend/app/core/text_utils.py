"""Shared text cleaning and parsing utilities."""
import json
from typing import Optional
from .config import AUTO_CORRECTION_METADATA_MARKERS


def clean_text(text: str) -> str:
    """
    Remove triple quotes and clean up text.
    Handles triple quotes on separate lines, at start/end, or standalone.
    Also handles escaped triple quotes from JSON.
    """
    if not text:
        return text

    # First, unescape any JSON-escaped characters
    text = text.replace('\\n', '\n').replace('\\\"', '"')

    # Remove any leading/trailing triple quotes from the entire text first
    text = text.strip()
    while text.startswith('"""'):
        text = text[3:].strip()
    while text.endswith('"""'):
        text = text[:-3].strip()

    # Split into lines to process individually
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        # Strip whitespace
        line = line.strip()

        # Skip empty lines and lines that are only triple quotes
        if not line or line == '"""' or line == '\\"\\"\\"' or line == '\\\\"""':
            continue

        # Remove leading/trailing triple quotes from individual lines
        while line.startswith('"""'):
            line = line[3:].strip()
        while line.endswith('"""'):
            line = line[:-3].strip()

        # Only add non-empty lines
        if line:
            cleaned_lines.append(line)

    # Join back and strip any leading/trailing whitespace
    return '\n'.join(cleaned_lines).strip()


def extract_transcript_only(text: str) -> str:
    """
    Extract only the actual transcript, removing auto-correction metadata.
    Removes sections like "Corrected errors include:", "Explanations:", etc.
    Uses markers defined in config.AUTO_CORRECTION_METADATA_MARKERS.
    """
    if not text:
        return text

    # Find the earliest metadata marker and remove everything from there onwards
    earliest_idx = len(text)  # Start with end of text

    for marker in AUTO_CORRECTION_METADATA_MARKERS:
        idx = text.find(marker)
        if idx != -1 and idx < earliest_idx:
            earliest_idx = idx

    # If a marker was found, remove everything from it onwards
    if earliest_idx < len(text):
        text = text[:earliest_idx]

    # Clean up - remove trailing blank lines and whitespace
    return text.strip()


def parse_summary(summary_content: Optional[str]) -> dict:
    """
    Parse summary JSON and extract clean summary text and meeting type.
    Returns dict with "summary" and "meeting_type" keys.
    """
    if not summary_content:
        return {"summary": None, "meeting_type": None}

    try:
        # First, try direct JSON parsing (might already be valid JSON from DB)
        data = json.loads(summary_content)
    except (json.JSONDecodeError, TypeError, ValueError):
        # If that fails, try cleaning the content first
        try:
            cleaned_content = clean_text(summary_content)
            data = json.loads(cleaned_content)
        except (json.JSONDecodeError, TypeError, ValueError):
            # If still not valid JSON, treat as plain text summary
            cleaned = clean_text(summary_content)
            return {
                "summary": cleaned if cleaned else None,
                "meeting_type": "General Meeting"
            }

    # Extract summary and meeting_type from JSON
    summary_text = data.get("summary", "")
    if isinstance(summary_text, str):
        summary_text = summary_text.strip()
        summary_text = clean_text(summary_text)

    meeting_type = data.get("meeting_type", "General Meeting")
    if isinstance(meeting_type, str):
        meeting_type = meeting_type.strip()

    return {
        "summary": summary_text if summary_text else None,
        "meeting_type": meeting_type
    }
