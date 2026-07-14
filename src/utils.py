"""
utils.py

Small, reusable helpers that don't belong to a specific feature module:
JSON persistence helpers, formatting helpers, and a cross-platform
non-blocking keyboard reader used by the typing engine.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------
def load_json(path: Path, default: Any) -> Any:
    """Load JSON from ``path``, returning ``default`` if the file is missing,
    empty, or corrupt. This keeps the app resilient to a user manually
    deleting or mangling a data file."""
    try:
        if not path.exists():
            return default
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return default
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> None:
    """Write ``data`` to ``path`` as pretty-printed JSON, creating parent
    directories if needed. Writes to a temp file first and replaces the
    target atomically so a crash mid-write can't corrupt existing data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(path)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def format_seconds(seconds: float) -> str:
    """Format a duration in seconds as M:SS."""
    seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


def clamp(value: float, low: float, high: float) -> float:
    """Restrict ``value`` to the inclusive range [low, high]."""
    return max(low, min(high, value))


def performance_rating(wpm: float) -> str:
    """Map a net WPM value to a human-readable performance tier."""
    from .constants import PERFORMANCE_RATINGS

    for threshold, label in PERFORMANCE_RATINGS:
        if wpm >= threshold:
            return label
    return PERFORMANCE_RATINGS[-1][1]


# ---------------------------------------------------------------------------
# Cross-platform non-blocking keyboard input
# ---------------------------------------------------------------------------
# The typing engine needs to read keystrokes one at a time, without waiting
# for Enter, and without blocking (so the live WPM/timer display can keep
# refreshing between keystrokes). The mechanism for this differs completely
# between Windows and POSIX systems, so we implement both behind one small
# interface: KeyReader.
class KeyReader:
    """Context manager providing non-blocking, single-character keyboard
    reads that work on both Windows and POSIX terminals.

    Usage:
        with KeyReader() as reader:
            key = reader.get_key(timeout=0.05)  # None if nothing pressed
    """

    def __init__(self) -> None:
        self._is_windows = os.name == "nt"
        self._old_settings = None
        self._fd: Optional[int] = None

    def __enter__(self) -> "KeyReader":
        if not self._is_windows:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._is_windows and self._old_settings is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)

    def get_key(self, timeout: float = 0.05) -> Optional[str]:
        """Return a single decoded key, or None if nothing was pressed
        within ``timeout`` seconds. Special keys are normalized to short
        string tokens: 'BACKSPACE', 'ESC', 'CTRL_C', 'ENTER', or the
        literal character typed.
        """
        if self._is_windows:
            return self._get_key_windows(timeout)
        return self._get_key_posix(timeout)

    def wait_key(self) -> str:
        """Block indefinitely until a key is pressed and return it. Used
        for single-keypress menu selection where no Enter should be
        required."""
        while True:
            key = self.get_key(timeout=0.1)
            if key is not None:
                return key

    # -- Windows implementation ------------------------------------------
    def _get_key_windows(self, timeout: float) -> Optional[str]:
        import msvcrt

        start = time.time()
        while time.time() - start < timeout:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    # Extended key (arrows, function keys) -- consume and
                    # ignore the second byte, we don't use these.
                    msvcrt.getwch()
                    return None
                if ch == "\x03":
                    return "CTRL_C"
                if ch == "\x1b":
                    return "ESC"
                if ch in ("\r", "\n"):
                    return "ENTER"
                if ch in ("\x08", "\x7f"):
                    return "BACKSPACE"
                return ch
            time.sleep(0.005)
        return None

    # -- POSIX implementation ---------------------------------------------
    def _get_key_posix(self, timeout: float) -> Optional[str]:
        import select

        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        ch = sys.stdin.read(1)
        if ch == "\x03":
            return "CTRL_C"
        if ch == "\x1b":
            return "ESC"
        if ch in ("\r", "\n"):
            return "ENTER"
        if ch in ("\x7f", "\x08"):
            return "BACKSPACE"
        return ch
