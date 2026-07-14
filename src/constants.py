"""
constants.py

Central location for fixed values used across the application:
file paths, color scheme, timing options, and menu labels.

Keeping these in one place avoids magic numbers/strings scattered
throughout the codebase and makes re-theming or re-configuring the
app a one-file change.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------
# ROOT_DIR points at the project root regardless of where the app is launched
# from, since __file__ gives us an absolute path to resolve against.
ROOT_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = ROOT_DIR / "assets"
DATA_DIR = ROOT_DIR / "data"

EASY_TEXT_FILE = ASSETS_DIR / "easy.txt"
MEDIUM_TEXT_FILE = ASSETS_DIR / "medium.txt"
HARD_TEXT_FILE = ASSETS_DIR / "hard.txt"
QUOTES_FILE = ASSETS_DIR / "quotes.txt"

LEADERBOARD_FILE = DATA_DIR / "leaderboard.json"
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------
DURATIONS = (15, 30, 60, 120)
DIFFICULTIES = ("Easy", "Medium", "Hard", "Random Quotes")

DIFFICULTY_FILE_MAP = {
    "Easy": EASY_TEXT_FILE,
    "Medium": MEDIUM_TEXT_FILE,
    "Hard": HARD_TEXT_FILE,
    "Random Quotes": QUOTES_FILE,
}

LEADERBOARD_MAX_ENTRIES = 20

# Minimum characters we want available for the longest test duration so the
# user never runs out of text before time expires. Paragraphs are recycled
# (re-shuffled and re-joined) as needed to reach this length.
MIN_CHARACTERS_REQUIRED = 2500

# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------
# A restrained, "premium" palette. No neon, no rainbow -- a small set of
# purposeful colors reused consistently across the UI.
THEME_PRESETS = {
    "Midnight Cyan": {
        "primary": "cyan",
        "secondary": "grey70",
        "accent": "gold3",
        "success": "green3",
        "error": "red3",
        "muted": "grey50",
        "background_panel": "grey15",
        "border": "grey35",
        "current_char": "black on cyan",
        "correct_char": "green3",
        "incorrect_char": "red3",
        "untyped_char": "grey58",
    },
    "Sunset Gold": {
        "primary": "gold3",
        "secondary": "grey70",
        "accent": "yellow",
        "success": "green3",
        "error": "red3",
        "muted": "grey50",
        "background_panel": "grey15",
        "border": "grey35",
        "current_char": "black on gold3",
        "correct_char": "green3",
        "incorrect_char": "red3",
        "untyped_char": "grey58",
    },
    "Classic Mono": {
        "primary": "white",
        "secondary": "grey74",
        "accent": "grey93",
        "success": "grey93",
        "error": "grey50",
        "muted": "grey50",
        "background_panel": "grey15",
        "border": "grey35",
        "current_char": "black on white",
        "correct_char": "grey93",
        "incorrect_char": "grey50 underline",
        "untyped_char": "grey58",
    },
}

# Default palette, used wherever a theme hasn't been resolved yet (e.g.
# module-level imports before Settings has loaded).
THEME = THEME_PRESETS["Midnight Cyan"]

PERFORMANCE_RATINGS = (
    (90, "Elite Typist"),
    (70, "Fast Typist"),
    (50, "Intermediate"),
    (30, "Beginner"),
    (0, "Needs Practice"),
)

APP_NAME = "Typing Speed Pro"
APP_VERSION = "1.0.0"

# Frame rate for the live typing display. 0.05s (~20 fps) is smooth enough
# for a terminal UI without hammering the CPU.
REFRESH_INTERVAL = 0.05

# Width (in characters) of the passage window shown around the cursor during
# a live test, so very long passages don't overflow narrow terminals.
PASSAGE_WINDOW_CHARS = 220
PASSAGE_WINDOW_LOOKBEHIND = 60
