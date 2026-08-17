"""Retry state wrapper delegating to db.py."""

from __future__ import annotations

from src.db import list_runs
from src.logger import get_logger

logger = get_logger(__name__)


class RetryState:
    """Manages incident retry logic using run history in the DB."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def get_retry_count(self, incident_id: str) -> int:
        """Return number of completed/failed runs for this incident."""
        runs = list_runs(self.db_path, incident_id)
        return len(
            [r for r in runs if r["status"] in ("completed", "failed", "cancelled")]
        )

    def should_retry(self, incident_id: str, max_retries: int) -> bool:
        """Return True if incident has remaining retry attempts."""
        count = self.get_retry_count(incident_id)
        return count < max_retries

    def increment_retry(self, incident_id: str) -> int:
        """Return the next run number (1-based)."""
        runs = list_runs(self.db_path, incident_id)
        return len(runs) + 1

    def reset(self, incident_id: str) -> None:
        """No-op: run history is immutable; reset is for interface compatibility."""
        logger.info("retry_state_reset_noop", incident_id=incident_id)
