import os
import time
import logging

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self, temp_dir="temp", max_age_hours=24):
        self.temp_dir = temp_dir
        self.max_age_seconds = max_age_hours * 3600

    def clean_stale_files(self):
        """Deletes files in the temp directory older than the specified age."""
        if not os.path.exists(self.temp_dir):
            return

        now = time.time()
        count = 0

        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)

            # Skip directories
            if not os.path.isfile(file_path):
                continue

            # Skip hidden files
            if filename.startswith('.'):
                continue

            file_age = now - os.path.getmtime(file_path)

            if file_age > self.max_age_seconds:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")

        if count > 0:
            logger.info(f"🧹 Cleanup: Deleted {count} stale audio files")
        return count
