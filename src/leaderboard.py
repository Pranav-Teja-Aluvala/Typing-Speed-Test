"""
leaderboard.py

Manages the local JSON leaderboard: adding new scores, trimming to the
top N, and sorting by different keys for display.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List

from .constants import LEADERBOARD_FILE, LEADERBOARD_MAX_ENTRIES
from .utils import load_json, save_json


@dataclass
class LeaderboardEntry:
    player_name: str
    wpm: float
    accuracy: float
    difficulty: str
    duration: int
    date: str  # ISO 8601 timestamp


class Leaderboard:
    """Wraps the leaderboard JSON file and exposes sorted views over it."""

    def __init__(self) -> None:
        self.entries: List[LeaderboardEntry] = self._load()

    def _load(self) -> List[LeaderboardEntry]:
        raw = load_json(LEADERBOARD_FILE, [])
        entries = []
        for item in raw:
            try:
                entries.append(LeaderboardEntry(**item))
            except TypeError:
                # Skip malformed records rather than crashing the app.
                continue
        return entries

    def _save(self) -> None:
        save_json(LEADERBOARD_FILE, [asdict(e) for e in self.entries])

    def add_score(
        self,
        player_name: str,
        wpm: float,
        accuracy: float,
        difficulty: str,
        duration: int,
    ) -> None:
        """Insert a new score, keep entries sorted by WPM descending, and
        trim to the configured maximum size."""
        entry = LeaderboardEntry(
            player_name=player_name or "Player",
            wpm=round(wpm, 2),
            accuracy=round(accuracy, 2),
            difficulty=difficulty,
            duration=duration,
            date=datetime.now().isoformat(timespec="seconds"),
        )
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.wpm, reverse=True)
        self.entries = self.entries[:LEADERBOARD_MAX_ENTRIES]
        self._save()

    def sorted_by(self, key: str) -> List[LeaderboardEntry]:
        """Return entries sorted by 'wpm', 'accuracy', or 'date'
        (all descending -- highest / most recent first)."""
        if key == "accuracy":
            return sorted(self.entries, key=lambda e: e.accuracy, reverse=True)
        if key == "date":
            return sorted(self.entries, key=lambda e: e.date, reverse=True)
        return sorted(self.entries, key=lambda e: e.wpm, reverse=True)

    def clear(self) -> None:
        self.entries = []
        self._save()

    def is_empty(self) -> bool:
        return len(self.entries) == 0
