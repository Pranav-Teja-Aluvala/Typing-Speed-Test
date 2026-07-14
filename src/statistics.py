"""
statistics.py

Tracks cumulative, persistent statistics across all test sessions:
averages, bests, totals, streaks, and most-played difficulty.
Backed by data/history.json, which stores one record per completed test
plus a small set of derived running totals for cheap incremental
updates (streaks).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from .constants import HISTORY_FILE
from .utils import load_json, save_json

DEFAULT_HISTORY = {
    "tests": [],              # list of per-test records
    "current_streak": 0,      # consecutive days with at least one test
    "longest_streak": 0,
    "last_test_date": None,   # ISO date string, used to compute streaks
}


@dataclass
class TestRecord:
    wpm: float
    accuracy: float
    difficulty: str
    duration: int
    characters_typed: int
    mistakes: int
    date: str


@dataclass
class StatsSummary:
    average_wpm: float = 0.0
    highest_wpm: float = 0.0
    average_accuracy: float = 0.0
    best_accuracy: float = 0.0
    total_tests: int = 0
    total_typing_time_seconds: int = 0
    total_characters_typed: int = 0
    total_mistakes: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    most_played_difficulty: str = "N/A"


class Statistics:
    """Wraps the persistent history JSON and computes derived summaries."""

    def __init__(self) -> None:
        raw = load_json(HISTORY_FILE, DEFAULT_HISTORY.copy())
        self.tests: List[dict] = raw.get("tests", [])
        self.current_streak: int = raw.get("current_streak", 0)
        self.longest_streak: int = raw.get("longest_streak", 0)
        self.last_test_date: Optional[str] = raw.get("last_test_date")

    def _save(self) -> None:
        save_json(
            HISTORY_FILE,
            {
                "tests": self.tests,
                "current_streak": self.current_streak,
                "longest_streak": self.longest_streak,
                "last_test_date": self.last_test_date,
            },
        )

    def record_test(
        self,
        wpm: float,
        accuracy: float,
        difficulty: str,
        duration: int,
        characters_typed: int,
        mistakes: int = 0,
    ) -> None:
        """Append a completed test to history and update the streak
        counters based on today's date."""
        today_str = date.today().isoformat()

        record = TestRecord(
            wpm=round(wpm, 2),
            accuracy=round(accuracy, 2),
            difficulty=difficulty,
            duration=duration,
            characters_typed=characters_typed,
            mistakes=mistakes,
            date=datetime.now().isoformat(timespec="seconds"),
        )
        self.tests.append(record.__dict__)

        self._update_streak(today_str)
        self._save()

    def _update_streak(self, today_str: str) -> None:
        if self.last_test_date is None:
            self.current_streak = 1
        elif self.last_test_date == today_str:
            pass  # Already played today; streak unchanged.
        else:
            last = date.fromisoformat(self.last_test_date)
            today = date.fromisoformat(today_str)
            if (today - last).days == 1:
                self.current_streak += 1
            else:
                self.current_streak = 1

        self.last_test_date = today_str
        self.longest_streak = max(self.longest_streak, self.current_streak)

    def summary(self) -> StatsSummary:
        if not self.tests:
            return StatsSummary(
                current_streak=self.current_streak,
                longest_streak=self.longest_streak,
            )

        total_tests = len(self.tests)
        avg_wpm = sum(t["wpm"] for t in self.tests) / total_tests
        highest_wpm = max(t["wpm"] for t in self.tests)
        avg_accuracy = sum(t["accuracy"] for t in self.tests) / total_tests
        best_accuracy = max(t["accuracy"] for t in self.tests)
        total_time = sum(t["duration"] for t in self.tests)
        total_chars = sum(t["characters_typed"] for t in self.tests)
        total_mistakes = sum(t.get("mistakes", 0) for t in self.tests)

        difficulty_counts: Dict[str, int] = {}
        for t in self.tests:
            difficulty_counts[t["difficulty"]] = difficulty_counts.get(t["difficulty"], 0) + 1
        most_played = max(difficulty_counts.items(), key=lambda kv: kv[1])[0]

        return StatsSummary(
            average_wpm=round(avg_wpm, 2),
            highest_wpm=round(highest_wpm, 2),
            average_accuracy=round(avg_accuracy, 2),
            best_accuracy=round(best_accuracy, 2),
            total_tests=total_tests,
            total_typing_time_seconds=total_time,
            total_characters_typed=total_chars,
            total_mistakes=total_mistakes,
            current_streak=self.current_streak,
            longest_streak=self.longest_streak,
            most_played_difficulty=most_played,
        )

    def reset(self) -> None:
        self.tests = []
        self.current_streak = 0
        self.longest_streak = 0
        self.last_test_date = None
        self._save()
