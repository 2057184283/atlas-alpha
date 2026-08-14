"""
Evidence Store
==============
Point-in-Time evidence storage.

Every evidence must pass temporal validation before being used in backtests.
This is the #1 defense against look-ahead bias.
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path
import json

from atlas.models import Evidence


class EvidenceStore:
    """
    Simple file-based evidence store.
    Production would use PostgreSQL + pgvector.
    """

    def __init__(self, data_dir: str = "data/evidence"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._mem: List[Evidence] = []

    def add(self, evidence: Evidence) -> None:
        """Store new evidence."""
        self._mem.append(evidence)
        self._persist()

    def query(
        self,
        ticker: Optional[str] = None,
        as_of: Optional[datetime] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Evidence]:
        """
        Query evidence with PIT filtering.

        If as_of is provided, only returns evidence available before that date.
        """
        results = self._mem.copy()

        if ticker:
            results = [e for e in results if ticker.lower() in e.source.lower()]

        if source:
            results = [e for e in results if e.source == source]

        if as_of:
            results = [e for e in results if e.is_valid_for_backtest(as_of)]

        return results[:limit]

    def _persist(self) -> None:
        """Save to disk."""
        path = self.data_dir / "evidence.json"
        data = [e.model_dump(mode="json") for e in self._mem]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> None:
        """Load from disk."""
        path = self.data_dir / "evidence.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._mem = [Evidence.model_validate(d) for d in data]
