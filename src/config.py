"""
config.py

Loads, validates, and saves user settings (theme, default duration,
default difficulty, sound toggle, player name). Settings are persisted
to data/settings.json.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .constants import DIFFICULTIES, DURATIONS, SETTINGS_FILE
from .utils import load_json, save_json

DEFAULT_SETTINGS = {
    "theme": "Midnight Cyan",
    "default_duration": 30,
    "default_difficulty": "Medium",
    "sound_enabled": True,
    "player_name": "Player",
}

AVAILABLE_THEMES = ("Midnight Cyan", "Sunset Gold", "Classic Mono")


@dataclass
class Settings:
    """In-memory representation of user settings with validation applied
    on load so a corrupted or hand-edited settings file can't crash the
    app or put it into an invalid state."""

    theme: str = DEFAULT_SETTINGS["theme"]
    default_duration: int = DEFAULT_SETTINGS["default_duration"]
    default_difficulty: str = DEFAULT_SETTINGS["default_difficulty"]
    sound_enabled: bool = DEFAULT_SETTINGS["sound_enabled"]
    player_name: str = DEFAULT_SETTINGS["player_name"]

    @classmethod
    def load(cls) -> "Settings":
        """Read settings.json (creating sane defaults if absent) and
        validate every field before returning a Settings instance."""
        raw = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
        merged = {**DEFAULT_SETTINGS, **raw}

        if merged["default_duration"] not in DURATIONS:
            merged["default_duration"] = DEFAULT_SETTINGS["default_duration"]
        if merged["default_difficulty"] not in DIFFICULTIES:
            merged["default_difficulty"] = DEFAULT_SETTINGS["default_difficulty"]
        if not isinstance(merged["sound_enabled"], bool):
            merged["sound_enabled"] = DEFAULT_SETTINGS["sound_enabled"]
        if not isinstance(merged["player_name"], str) or not merged["player_name"].strip():
            merged["player_name"] = DEFAULT_SETTINGS["player_name"]
        if merged["theme"] not in AVAILABLE_THEMES:
            merged["theme"] = DEFAULT_SETTINGS["theme"]

        instance = cls(
            theme=merged["theme"],
            default_duration=merged["default_duration"],
            default_difficulty=merged["default_difficulty"],
            sound_enabled=merged["sound_enabled"],
            player_name=merged["player_name"],
        )
        # Persist back immediately in case validation corrected anything,
        # so a corrupted file is healed on first load rather than re-failing
        # validation on every subsequent run.
        instance.save()
        return instance

    def save(self) -> None:
        save_json(SETTINGS_FILE, asdict(self))

    def reset(self) -> None:
        defaults = DEFAULT_SETTINGS.copy()
        self.theme = defaults["theme"]
        self.default_duration = defaults["default_duration"]
        self.default_difficulty = defaults["default_difficulty"]
        self.sound_enabled = defaults["sound_enabled"]
        self.player_name = defaults["player_name"]
        self.save()
