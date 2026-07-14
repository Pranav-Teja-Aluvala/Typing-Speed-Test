"""
typing.py

The core typing-test engine: tracks what the user has typed against a
target passage, computes live and final statistics (WPM, accuracy,
mistakes), and exposes the state the UI layer needs to render the
live view. This module has no Rich/console dependency so it can be
tested in isolation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TestResult:
    """Final, immutable summary of a completed test."""

    gross_wpm: float
    net_wpm: float
    accuracy: float
    mistakes: int
    correct_characters: int
    incorrect_characters: int
    characters_typed: int
    time_taken: float
    difficulty: str
    duration: int
    paragraph_excerpt: str


class TypingTestEngine:
    """Drives a single typing test session.

    The engine is fed key events one at a time via `process_key` and does
    not itself read from the keyboard or render anything -- that's the
    job of utils.KeyReader and ui.py respectively. This separation keeps
    the scoring logic simple to unit test.
    """

    def __init__(self, passage: str, duration: int, difficulty: str) -> None:
        self.passage = passage
        self.duration = duration
        self.difficulty = difficulty

        self.typed: List[str] = []
        self.total_mistakes = 0  # cumulative wrong keystrokes, never decreases
        self.started = False
        self.finished = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self.started = True
        self.start_time = time.perf_counter()

    def _finish(self) -> None:
        if not self.finished:
            self.finished = True
            self.end_time = time.perf_counter()

    # -- input handling ----------------------------------------------------
    def process_key(self, key: str) -> None:
        """Feed one normalized key event (as produced by KeyReader) into
        the engine. No-ops once the test has finished."""
        if self.finished:
            return

        if not self.started:
            self.start()

        if key == "BACKSPACE":
            if self.typed:
                self.typed.pop()
            return

        if key in ("CTRL_C", "ESC"):
            self._finish()
            return

        if key == "ENTER":
            key = " "  # Treat Enter as a space so passages never stall.

        if len(key) != 1:
            return  # Ignore any other unmapped control tokens.

        position = len(self.typed)
        if position >= len(self.passage):
            return

        self.typed.append(key)
        if key != self.passage[position]:
            self.total_mistakes += 1

        if len(self.typed) >= len(self.passage):
            self._finish()

    # -- live state for the UI -------------------------------------------
    def elapsed_seconds(self) -> float:
        if not self.started or self.start_time is None:
            return 0.0
        end = self.end_time if self.finished else time.perf_counter()
        return max(0.0, end - self.start_time)

    def remaining_seconds(self) -> float:
        return max(0.0, self.duration - self.elapsed_seconds())

    def is_time_up(self) -> bool:
        return self.started and self.elapsed_seconds() >= self.duration

    def correct_character_count(self) -> int:
        return sum(1 for i, ch in enumerate(self.typed) if ch == self.passage[i])

    def incorrect_character_count(self) -> int:
        return len(self.typed) - self.correct_character_count()

    def characters_typed(self) -> int:
        return len(self.typed)

    def current_gross_wpm(self) -> float:
        minutes = self.elapsed_seconds() / 60
        if minutes <= 0:
            return 0.0
        return (len(self.typed) / 5) / minutes

    def current_net_wpm(self) -> float:
        minutes = self.elapsed_seconds() / 60
        if minutes <= 0:
            return 0.0
        gross_words = len(self.typed) / 5
        net_words = max(0.0, gross_words - self.incorrect_character_count() / 5)
        return net_words / minutes

    def current_accuracy(self) -> float:
        if not self.typed:
            return 100.0
        return (self.correct_character_count() / len(self.typed)) * 100

    # -- finalization ------------------------------------------------------
    def build_result(self) -> TestResult:
        """Compute the final TestResult. Safe to call whether the test
        ended naturally (time up / passage complete) or was cut short."""
        self._finish()
        time_taken = self.elapsed_seconds()
        correct = self.correct_character_count()
        incorrect = self.incorrect_character_count()
        total_typed = self.characters_typed()

        minutes = time_taken / 60 if time_taken > 0 else (self.duration / 60)
        minutes = max(minutes, 1 / 60)  # guard against div-by-zero on instant quits

        gross_wpm = (total_typed / 5) / minutes
        net_wpm = max(0.0, ((total_typed / 5) - incorrect / 5) / minutes)
        accuracy = (correct / total_typed * 100) if total_typed else 0.0

        excerpt = self.passage[:80] + ("..." if len(self.passage) > 80 else "")

        return TestResult(
            gross_wpm=round(gross_wpm, 2),
            net_wpm=round(net_wpm, 2),
            accuracy=round(accuracy, 2),
            mistakes=self.total_mistakes,
            correct_characters=correct,
            incorrect_characters=incorrect,
            characters_typed=total_typed,
            time_taken=round(time_taken, 2),
            difficulty=self.difficulty,
            duration=self.duration,
            paragraph_excerpt=excerpt,
        )
