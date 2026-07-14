"""
paragraphs.py

Loads the raw text assets (easy/medium/hard sentence banks and the
quotes file) and assembles them into a single passage long enough to
outlast any supported test duration, even at very high WPM.

Lines are shuffled independently on every call so consecutive tests
don't repeat the same passage, and are looped with re-shuffling if the
source file alone isn't long enough to reach MIN_CHARACTERS_REQUIRED.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import List

from .constants import DIFFICULTY_FILE_MAP, MIN_CHARACTERS_REQUIRED


class ParagraphError(Exception):
    """Raised when a text asset is missing, empty, or unreadable."""


def _load_lines(path: Path) -> List[str]:
    """Read non-empty, stripped lines from a text asset file."""
    if not path.exists():
        raise ParagraphError(
            f"Missing text asset: {path.name}. Reinstall the app or restore "
            f"the file at {path}."
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParagraphError(f"Could not read {path.name}: {exc}") from exc

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise ParagraphError(f"Text asset {path.name} is empty.")
    return lines


def get_passage(difficulty: str, min_characters: int = MIN_CHARACTERS_REQUIRED) -> str:
    """Build a single-space-joined passage for ``difficulty`` that is at
    least ``min_characters`` long, shuffling (and re-shuffling, looping as
    needed) the source lines so passages vary between tests.

    Raises ParagraphError if the difficulty is unknown or its source file
    can't be read.
    """
    path = DIFFICULTY_FILE_MAP.get(difficulty)
    if path is None:
        raise ParagraphError(f"Unknown difficulty: {difficulty!r}")

    source_lines = _load_lines(path)

    pieces: List[str] = []
    total_length = 0
    while total_length < min_characters:
        shuffled = source_lines.copy()
        random.shuffle(shuffled)
        for line in shuffled:
            pieces.append(line)
            # +1 accounts for the joining space added between pieces.
            total_length += len(line) + 1
            if total_length >= min_characters:
                break

    return " ".join(pieces)
