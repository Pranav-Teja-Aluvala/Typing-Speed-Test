"""
game.py

The application controller: owns the main menu loop and wires together
the UI layer, the typing engine, persisted settings, leaderboard, and
statistics. This is the only module that knows about the overall
program flow.
"""

from __future__ import annotations

from rich.live import Live

from .config import Settings
from .constants import REFRESH_INTERVAL
from .leaderboard import Leaderboard
from .paragraphs import ParagraphError, get_passage
from .statistics import Statistics
from .typing import TypingTestEngine
from .ui import UI
from .utils import KeyReader


class Game:
    """Top-level application controller."""

    def __init__(self) -> None:
        self.settings = Settings.load()
        self.ui = UI(theme_name=self.settings.theme)
        self.leaderboard = Leaderboard()
        self.stats = Statistics()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        actions = {
            "1": self.start_test,
            "2": self.practice_mode,
            "3": self.view_leaderboard,
            "4": self.view_statistics,
            "5": self.open_settings,
        }
        while True:
            choice = self.ui.main_menu()
            if choice == "6":
                self.ui.clear()
                self.ui.console.print("Thanks for typing. Goodbye!")
                return
            action = actions.get(choice)
            if action:
                try:
                    action()
                except ParagraphError as exc:
                    self.ui.error(str(exc))
                    self.ui.pause()

    # ------------------------------------------------------------------
    # Test flow (shared by Start Test and Practice Mode)
    # ------------------------------------------------------------------
    def _run_session(self, duration: int, difficulty: str, timed: bool) -> None:
        passage = get_passage(difficulty)
        engine = TypingTestEngine(passage, duration, difficulty)

        self.ui.show_get_ready()
        self.ui.countdown(3)
        self.ui.clear()

        with KeyReader() as reader:
            with Live(
                self.ui.build_test_renderable(engine),
                refresh_per_second=int(1 / REFRESH_INTERVAL),
                console=self.ui.console,
                screen=False,
                transient=False,
            ) as live:
                while not engine.finished:
                    if timed and engine.is_time_up():
                        break
                    key = reader.get_key(timeout=REFRESH_INTERVAL)
                    if key:
                        engine.process_key(key)
                    live.update(self.ui.build_test_renderable(engine))

        result = engine.build_result()

        is_new_best = False
        if timed:
            previous_best = max((e.wpm for e in self.leaderboard.entries), default=0.0)
            is_new_best = result.net_wpm > previous_best and result.characters_typed > 0

            self.stats.record_test(
                wpm=result.net_wpm,
                accuracy=result.accuracy,
                difficulty=result.difficulty,
                duration=result.duration,
                characters_typed=result.characters_typed,
                mistakes=result.mistakes,
            )
            if result.characters_typed > 0:
                self.leaderboard.add_score(
                    player_name=self.settings.player_name,
                    wpm=result.net_wpm,
                    accuracy=result.accuracy,
                    difficulty=result.difficulty,
                    duration=result.duration,
                )

        self.ui.show_report(result, is_new_best)
        self.ui.pause()

    def start_test(self) -> None:
        duration = self.ui.select_duration(self.settings.default_duration, title="Start Test")
        difficulty = self.ui.select_difficulty(self.settings.default_difficulty, title="Start Test")
        self._run_session(duration, difficulty, timed=True)

    def practice_mode(self) -> None:
        """Untimed practice: type a full passage at your own pace with no
        score saved to the leaderboard or statistics. A generous 999s
        ceiling still applies so the engine's timer math stays well-defined."""
        difficulty = self.ui.select_difficulty(self.settings.default_difficulty, title="Practice Mode")
        self._run_session(duration=999, difficulty=difficulty, timed=False)

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------
    def view_leaderboard(self) -> None:
        entries = self.leaderboard.sorted_by("wpm")
        self.ui.show_leaderboard(entries)
        self.ui.pause()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def view_statistics(self) -> None:
        summary = self.stats.summary()
        self.ui.show_statistics(summary)
        self.ui.pause()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def open_settings(self) -> None:
        """Settings is one persistent screen: settings_menu() redraws the
        current values plus the numbered actions and blocks for a single
        keypress. Toggles and resets apply immediately and loop straight
        back to a freshly redrawn screen -- only actions that genuinely
        need typed text (player name) or a yes/no stop to ask for it."""
        while True:
            choice = self.ui.settings_menu(self.settings)

            if choice == "1":
                self.settings.player_name = self.ui.prompt_player_name(self.settings.player_name)
                self.settings.save()
            elif choice == "2":
                self.settings.default_duration = self.ui.select_duration(self.settings.default_duration)
                self.settings.save()
            elif choice == "3":
                self.settings.default_difficulty = self.ui.select_difficulty(self.settings.default_difficulty)
                self.settings.save()
            elif choice == "4":
                self.settings.theme = self.ui.select_theme(self.settings.theme)
                self.ui.set_theme(self.settings.theme)
                self.settings.save()
            elif choice == "5":
                self.settings.sound_enabled = not self.settings.sound_enabled
                self.settings.save()
            elif choice == "6":
                if self.ui.confirm("Reset all statistics? This cannot be undone."):
                    self.stats.reset()
                    self.ui.flash("Statistics reset.")
            elif choice == "7":
                if self.ui.confirm("Reset the leaderboard? This cannot be undone."):
                    self.leaderboard.clear()
                    self.ui.flash("Leaderboard reset.")
            elif choice == "8":
                return
