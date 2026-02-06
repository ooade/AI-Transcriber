
import jiwer
from sqlalchemy.orm import Session
from ..models import Transcription, CorrectedTranscript
from sqlalchemy import func

class AccuracyService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """
        Calculates Word Error Rate between reference (ground truth) and hypothesis (prediction).
        """
        if not reference or not hypothesis:
            return 1.0 # Max error if empty

        return jiwer.wer(reference, hypothesis)

    def get_global_metrics(self):
        """
        Aggregates metrics for the Insights dashboard.
        """
        # 1. Total Corrections
        total_errors = self.db.query(func.count(CorrectedTranscript.id)).scalar()

        # 2. Average WER (Simulated for now based on available corrections)
        # In a real system, we'd store the WER on the CorrectedTranscript record
        # but here we'll compute it on the fly for the last 50 corrections
        corrections = self.db.query(CorrectedTranscript).order_by(
            CorrectedTranscript.corrected_at.desc()
        ).limit(50).all()

        total_wer = 0
        count = 0

        for correction in corrections:
            # Find original raw transcript
            # Note: We need to traverse back to Transcription -> RawTranscript
            transcription = correction.transcription
            if transcription and transcription.raw_transcript:
                 wer = self.calculate_wer(correction.content, transcription.raw_transcript.content)
                 total_wer += wer
                 count += 1

        avg_wer = total_wer / count if count > 0 else 0.0

        # 3. Simulate specific error types (Stub logic for demo)
        by_type = {
            "substitutions": int(total_errors * 0.6),
            "deletions": int(total_errors * 0.3),
            "insertions": int(total_errors * 0.1)
        }

        # 4. Frequent Errors (Stub logic for demo, usually comes from ErrorAnalysisService)
        frequent_errors = [
            {"word": "Antigravity", "count": 12},
            {"word": "Cortex", "count": 8},
            {"word": "Ademola", "count": 5}
        ]

        return {
            "total_errors": total_errors,
            "average_wer": avg_wer,
            "by_type": by_type,
            "frequent_errors": frequent_errors
        }
