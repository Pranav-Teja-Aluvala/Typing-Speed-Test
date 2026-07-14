"""
ui.py

All Rich-based rendering lives here: menus, panels, tables, and the
live typing view. Keeping presentation isolated from game logic
(game.py) and scoring logic (typing.py) means any of the three can
change independently -- this module owns *how things look*, nothing
about *what happens*.

Design language
----------------
- Every screen fully replaces the previous one (``clear()`` first) --
  nothing scrolls past like terminal history; it should feel like
  navigating panes in a real application, not reading a log.
- A restrained palette: white, grey, cyan, gold, green, red. Color is
  used to draw attention (correctness, ratings, warnings), never as
  decoration.
- Box styles are chosen deliberately per section (ROUNDED for cards
  and menus, HEAVY for the focal typing panel, DOUBLE for the main
  menu and the result screen) so the hierarchy reads at a glance --
  not every element gets a border; whitespace does some of the work.
- Every menu is a single keypress (via KeyReader) -- no typing a
  number and pressing Enter. Difficulty/duration/theme are chosen by
  number rather than by typing a name, which also removes any
  case-sensitivity concern entirely.
"""

from __future__ import annotations

import time
from itertools import zip_longest
from typing import List, Sequence

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .constants import (
    APP_NAME,
    APP_VERSION,
    DIFFICULTIES,
    DURATIONS,
    PASSAGE_WINDOW_CHARS,
    PASSAGE_WINDOW_LOOKBEHIND,
    THEME,
    THEME_PRESETS,
)
from .leaderboard import LeaderboardEntry
from .statistics import StatsSummary
from .typing import TestResult, TypingTestEngine
from .utils import KeyReader, format_seconds, performance_rating

# Panels are capped at this width so the layout stays readable and
# consistent instead of stretching edge-to-edge on very wide terminals.
MAX_UI_WIDTH = 100
MIN_TWO_COLUMN_WIDTH = 70


class UI:
    """Thin wrapper around a Rich Console providing every screen the app
    needs. Methods either print directly or return a Rich renderable for
    the caller (game.py) to display inside a Live context."""

    def __init__(self, theme_name: str = "Midnight Cyan") -> None:
        # Cap width to MAX_UI_WIDTH but never exceed the real terminal, so
        # the UI degrades gracefully on narrow windows instead of
        # overflowing or wrapping mid-panel.
        probe_width = Console().size.width or MAX_UI_WIDTH
        self.width = min(MAX_UI_WIDTH, probe_width)
        self.console = Console(width=self.width)
        self.theme = THEME_PRESETS.get(theme_name, THEME)

    def set_theme(self, theme_name: str) -> None:
        self.theme = THEME_PRESETS.get(theme_name, THEME)

    # ------------------------------------------------------------------
    # Single-keypress selection
    # ------------------------------------------------------------------
    def _read_choice(self, valid_keys: Sequence[str]) -> str:
        """Block for a single keypress matching one of ``valid_keys``
        (case-insensitive), no Enter required. Any other key is silently
        ignored and the wait continues."""
        valid = {k.lower() for k in valid_keys}
        with KeyReader() as reader:
            while True:
                key = reader.wait_key()
                if key and key.lower() in valid:
                    return key.lower()

    # ------------------------------------------------------------------
    # Screen scaffolding
    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.console.clear()

    def screen(self, title: str, subtitle: str = "") -> None:
        """Start a brand-new screen: clear, then print the compact
        app header. Every top-level screen calls this first so nothing
        ever stacks underneath a previous one."""
        self.clear()
        title_line = Text()
        title_line.append(APP_NAME, style=f"bold {self.theme['primary']}")
        title_line.append(f"  v{APP_VERSION}", style=self.theme["muted"])
        self.console.print(Align.center(title_line))
        if title:
            self.console.print(Align.center(Text(title, style=f"bold {self.theme['secondary']}")))
        if subtitle:
            self.console.print(Align.center(Text(subtitle, style=self.theme["muted"])))
        self.console.print(Rule(style=self.theme["border"]))

    # Kept for backward-compatible call sites; behaves like screen().
    def header(self, subtitle: str = "") -> None:
        self.screen("", subtitle)

    def status_bar(self, hint: str) -> None:
        """A slim, unboxed hint line -- the 'bottom status bar' style
        used by tools like lazygit, not another panel."""
        self.console.print()
        self.console.print(Align.center(Text(hint, style=self.theme["muted"])))

    def pause(self, message: str = "Press any key to continue") -> None:
        """Wait for a single keypress (no Enter needed) before moving on."""
        self.status_bar(message)
        with KeyReader() as reader:
            reader.wait_key()

    def flash(self, message: str, success: bool = True) -> None:
        """A short-lived confirmation line that clears itself after a
        beat, instead of blocking on a keypress -- used for quick
        feedback (a reset, a toggle) that shouldn't interrupt flow."""
        color = self.theme["success"] if success else self.theme["error"]
        self.console.print(Align.center(Text(message, style=f"bold {color}")))
        time.sleep(0.7)

    def error(self, message: str) -> None:
        self.console.print(Panel(message, style=self.theme["error"], title="Error",
                                  border_style=self.theme["error"], box=box.ROUNDED, width=self.width))

    def info(self, message: str) -> None:
        self.console.print(Panel(message, style=self.theme["secondary"],
                                  border_style=self.theme["border"], box=box.ROUNDED, width=self.width))

    def success(self, message: str) -> None:
        self.console.print(Panel(message, style=self.theme["success"],
                                  border_style=self.theme["success"], box=box.ROUNDED, width=self.width))

    # ------------------------------------------------------------------
    # Shared: numbered option list inside a rounded panel
    # ------------------------------------------------------------------
    def _boxed_options(self, rows: Sequence[tuple], title: str = "") -> None:
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="right", style=f"bold {self.theme['accent']}")
        table.add_column(justify="left", style="white")
        for key, label in rows:
            table.add_row(f"[{key}]", label)

        self.console.print(
            Panel(Align.center(table), title=title, border_style=self.theme["border"],
                  box=box.ROUNDED, padding=(1, 3), width=self.width)
        )

    def _stat_card(self, label: str, value: str, color: str) -> Panel:
        """A single small 'dashboard card': big value on top, quiet
        label underneath -- the btop-style building block reused by
        the live typing HUD and the statistics dashboard. Each line is
        centered explicitly (rather than relying on Text justification
        inside a Panel) so values line up cleanly card to card."""
        content = Group(
            Align.center(Text(value, style=f"bold {color}")),
            Align.center(Text(label.upper(), style=self.theme["muted"])),
        )
        return Panel(content, border_style=self.theme["border"], box=box.ROUNDED, padding=(0, 1))

    # ------------------------------------------------------------------
    # Main menu -- one full-screen centered panel
    # ------------------------------------------------------------------
    def main_menu(self) -> str:
        self.clear()

        title = Text(APP_NAME, style=f"bold {self.theme['primary']}", justify="center")
        subtitle = Text("Precision. Speed. Progress.", style=self.theme["muted"], justify="center")

        rows = [
            ("1", "Start Test"),
            ("2", "Practice Mode"),
            ("3", "Leaderboard"),
            ("4", "Statistics"),
            ("5", "Settings"),
            ("6", "Exit"),
        ]
        options = Table.grid(padding=(0, 3))
        options.add_column(justify="right", style=f"bold {self.theme['accent']}")
        options.add_column(justify="left", style="white")
        for key, label in rows:
            options.add_row(f"[{key}]", label)

        body = Group(
            title,
            subtitle,
            Text(""),
            Rule(style=self.theme["border"]),
            Text(""),
            Align.center(options),
        )

        panel = Panel(
            body,
            box=box.DOUBLE,
            border_style=self.theme["primary"],
            padding=(1, 4),
            width=self.width,
        )

        self.console.print(Align.center(panel))
        self.status_bar("Press a number key to select")
        return self._read_choice([r[0] for r in rows])

    # ------------------------------------------------------------------
    # Start Test flow -- each step is its own full screen
    # ------------------------------------------------------------------
    def select_duration(self, default: int, title: str = "Select Duration") -> int:
        self.screen(title)
        rows = [
            (str(i), f"{seconds} seconds" + ("   (default)" if seconds == default else ""))
            for i, seconds in enumerate(DURATIONS, start=1)
        ]
        self._boxed_options(rows)
        self.status_bar("Press a number key to select duration")
        key = self._read_choice([r[0] for r in rows])
        return DURATIONS[int(key) - 1]

    def select_difficulty(self, default: str, title: str = "Select Difficulty") -> str:
        self.screen(title)
        rows = [
            (str(i), name + ("   (default)" if name == default else ""))
            for i, name in enumerate(DIFFICULTIES, start=1)
        ]
        self._boxed_options(rows)
        self.status_bar("Press a number key to select difficulty")
        key = self._read_choice([r[0] for r in rows])
        return DIFFICULTIES[int(key) - 1]

    def select_theme(self, current: str) -> str:
        names = list(THEME_PRESETS.keys())
        self.screen("Select Theme")
        rows = [
            (str(i), name + ("   (current)" if name == current else ""))
            for i, name in enumerate(names, start=1)
        ]
        self._boxed_options(rows)
        self.status_bar("Press a number key to select theme")
        key = self._read_choice([r[0] for r in rows])
        return names[int(key) - 1]

    def show_get_ready(self) -> None:
        self.screen("Get Ready")
        self.console.print(
            Align.center(
                Panel(
                    "Type the passage exactly as shown.\nBackspace corrects mistakes. Esc ends the test early.",
                    border_style=self.theme["border"],
                    box=box.ROUNDED,
                    padding=(1, 4),
                )
            )
        )

    def countdown(self, seconds: int = 3) -> None:
        for n in range(seconds, 0, -1):
            self.console.print(Align.center(Text(str(n), style=f"bold {self.theme['accent']}")))
            time.sleep(0.6)
        self.console.print(Align.center(Text("Go", style=f"bold {self.theme['success']}")))
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Live typing view (Monkeytype-style dashboard)
    # ------------------------------------------------------------------
    def build_test_renderable(self, engine: TypingTestEngine) -> Group:
        """Build the full live-test view: a row of small stat cards, a
        progress bar, the large focal typing panel, and a slim status
        bar. Returned as a Group (not wrapped in an outer border) so the
        typing panel remains the clear visual focus. Called on every
        refresh tick from game.py."""
        cards = Columns(
            [
                self._stat_card("WPM", f"{engine.current_net_wpm():.0f}", self.theme["primary"]),
                self._stat_card("Accuracy", f"{engine.current_accuracy():.0f}%", self.theme["success"]),
                self._stat_card("Time Left", format_seconds(engine.remaining_seconds()), self.theme["accent"]),
                self._stat_card("Mistakes", str(engine.total_mistakes), self.theme["error"]),
                self._stat_card("Typed", str(engine.characters_typed()), self.theme["secondary"]),
            ],
            equal=True,
            expand=True,
        )

        progress_fraction = min(1.0, engine.characters_typed() / max(1, len(engine.passage)))
        bar = ProgressBar(
            total=1.0,
            completed=progress_fraction,
            width=self.width - 4,
            complete_style=self.theme["primary"],
            style=self.theme["border"],
        )

        passage_panel = Panel(
            self._render_passage(engine),
            box=box.HEAVY,
            border_style=self.theme["primary"],
            padding=(1, 2),
            width=self.width,
        )

        status = Align.center(
            Text.assemble(
                ("ESC", f"bold {self.theme['error']}"), (" quit early    ", self.theme["muted"]),
                ("BACKSPACE", f"bold {self.theme['accent']}"), (" correct a mistake", self.theme["muted"]),
            )
        )

        return Group(cards, Text(""), Align.center(bar), Text(""), passage_panel, status)

    def _render_passage(self, engine: TypingTestEngine) -> Text:
        """Render the passage with per-character coloring: typed-correct
        characters in green, typed-incorrect characters in red/underline
        (showing the target character, not what was mistakenly pressed,
        so the user always sees what they still need to type), the
        current character inverse-highlighted as a cursor, and the rest
        dim/untyped."""
        text = Text()
        typed = engine.typed
        passage = engine.passage
        cursor = len(typed)

        # Only show a window of the passage around the cursor so very long
        # passages don't overflow the terminal.
        window = PASSAGE_WINDOW_CHARS
        start = max(0, cursor - PASSAGE_WINDOW_LOOKBEHIND)
        end = min(len(passage), start + window)
        if end - start < window:
            start = max(0, end - window)

        for i in range(start, end):
            char = passage[i]
            if i < cursor:
                if typed[i] == char:
                    text.append(char, style=self.theme["correct_char"])
                else:
                    text.append(char, style=f"{self.theme['incorrect_char']} underline")
            elif i == cursor:
                text.append(char if char != " " else "\u2423", style=self.theme["current_char"])
            else:
                text.append(char, style=self.theme["untyped_char"])
        return text

    # ------------------------------------------------------------------
    # Result screen -- premium summary
    # ------------------------------------------------------------------
    def show_report(self, result: TestResult, is_new_best: bool) -> None:
        self.screen("Test Complete")

        rating = performance_rating(result.net_wpm)

        table = Table.grid(padding=(0, 4), expand=False)
        table.add_column(justify="left", style=self.theme["secondary"])
        table.add_column(justify="left", style="bold white")
        table.add_column(justify="left", style=self.theme["secondary"])
        table.add_column(justify="left", style="bold white")
        table.add_row("Net WPM", f"{result.net_wpm:.1f}", "Gross WPM", f"{result.gross_wpm:.1f}")
        table.add_row("Accuracy", f"{result.accuracy:.1f}%", "Mistakes", str(result.mistakes))
        table.add_row("Correct Chars", str(result.correct_characters), "Incorrect Chars", str(result.incorrect_characters))
        table.add_row("Characters Typed", str(result.characters_typed), "Time Taken", format_seconds(result.time_taken))
        table.add_row("Difficulty", result.difficulty, "Duration", f"{result.duration}s")

        blocks: List = []
        if is_new_best:
            blocks.append(Align.center(Text("NEW PERSONAL BEST", style=f"bold {self.theme['accent']}")))
            blocks.append(Text(""))
        blocks.append(Align.center(Text(f"{result.net_wpm:.1f} WPM", style=f"bold {self.theme['primary']}")))
        blocks.append(Align.center(Text(rating, style=f"bold {self.theme['success']}")))
        blocks.append(Text(""))
        blocks.append(Rule(style=self.theme["border"]))
        blocks.append(Text(""))
        blocks.append(Align.center(table))

        panel = Panel(
            Group(*blocks),
            box=box.DOUBLE,
            border_style=self.theme["primary"],
            padding=(2, 4),
            width=self.width,
        )
        self.console.print(Align.center(panel))
        self.console.print()
        self.console.print(
            Align.center(Text(f'"{result.paragraph_excerpt}"', style=f"italic {self.theme['muted']}"))
        )

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------
    def show_leaderboard(self, entries: Sequence[LeaderboardEntry]) -> None:
        """Always shows the top entries sorted by WPM (highest first) --
        no sort prompt, since WPM is what a leaderboard is for."""
        self.screen("Leaderboard", f"Top {len(entries)} by WPM")

        if not entries:
            self.info("No scores yet. Complete a test to appear on the leaderboard.")
            return

        table = Table(
            box=box.SIMPLE_HEAVY,
            border_style=self.theme["border"],
            header_style=f"bold {self.theme['primary']}",
            row_styles=["", "on grey11"],
            width=self.width,
        )
        table.add_column("#", justify="right", width=3)
        table.add_column("Player", ratio=2)
        table.add_column("WPM", justify="right")
        table.add_column("Accuracy", justify="right")
        table.add_column("Difficulty")
        table.add_column("Duration", justify="right")
        table.add_column("Date")

        for i, entry in enumerate(entries, start=1):
            rank_style = f"bold {self.theme['accent']}" if i <= 3 else self.theme["secondary"]
            table.add_row(
                Text(str(i), style=rank_style),
                entry.player_name,
                f"{entry.wpm:.1f}",
                f"{entry.accuracy:.1f}%",
                entry.difficulty,
                f"{entry.duration}s",
                entry.date.split("T")[0],
            )
        self.console.print(table)

    # ------------------------------------------------------------------
    # Statistics -- dashboard of small cards
    # ------------------------------------------------------------------
    def show_statistics(self, summary: StatsSummary) -> None:
        self.screen("Your Statistics")

        if summary.total_tests == 0:
            self.info("No tests recorded yet. Complete a test to build up statistics.")
            return

        cards = [
            self._stat_card("Tests Played", str(summary.total_tests), self.theme["primary"]),
            self._stat_card("Average WPM", f"{summary.average_wpm:.1f}", self.theme["primary"]),
            self._stat_card("Highest WPM", f"{summary.highest_wpm:.1f}", self.theme["accent"]),
            self._stat_card("Average Accuracy", f"{summary.average_accuracy:.1f}%", self.theme["success"]),
            self._stat_card("Best Accuracy", f"{summary.best_accuracy:.1f}%", self.theme["success"]),
            self._stat_card("Typing Time", format_seconds(summary.total_typing_time_seconds), self.theme["secondary"]),
            self._stat_card("Characters Typed", str(summary.total_characters_typed), self.theme["secondary"]),
            self._stat_card("Mistakes", str(summary.total_mistakes), self.theme["error"]),
            self._stat_card("Most Played", summary.most_played_difficulty, self.theme["secondary"]),
        ]

        columns = 2 if self.width >= MIN_TWO_COLUMN_WIDTH else 1
        grid = Table.grid(padding=(1, 1), expand=True)
        for _ in range(columns):
            grid.add_column(ratio=1)
        for chunk in zip_longest(*[iter(cards)] * columns, fillvalue=None):
            grid.add_row(*[c if c is not None else "" for c in chunk])

        self.console.print(grid)

    # ------------------------------------------------------------------
    # Settings -- compact, values highlighted inline
    # ------------------------------------------------------------------
    def settings_menu(self, settings) -> str:
        """One compact screen: each editable setting shows its current
        value inline (highlighted), plus a short list of actions below a
        divider. Blocks for a single keypress -- no giant menu, no
        separate summary panel to re-read."""
        self.screen("Settings")

        rows = Table.grid(padding=(0, 2))
        rows.add_column(justify="right", style=f"bold {self.theme['accent']}")
        rows.add_column(justify="left", style=self.theme["secondary"], min_width=22)
        rows.add_column(justify="left", style=f"bold {self.theme['primary']}")
        rows.add_row("[1]", "Player Name", settings.player_name)
        rows.add_row("[2]", "Default Duration", f"{settings.default_duration}s")
        rows.add_row("[3]", "Default Difficulty", settings.default_difficulty)
        rows.add_row("[4]", "Theme", settings.theme)
        rows.add_row("[5]", "Sound", "On" if settings.sound_enabled else "Off")

        actions = Table.grid(padding=(0, 2))
        actions.add_column(justify="right", style=f"bold {self.theme['error']}")
        actions.add_column(justify="left", style="white")
        actions.add_row("[6]", "Reset Statistics")
        actions.add_row("[7]", "Reset Leaderboard")
        actions.add_row("[8]", "Back to Main Menu")

        body = Group(
            Align.center(rows),
            Text(""),
            Rule(style=self.theme["border"]),
            Text(""),
            Align.center(actions),
        )
        self.console.print(
            Panel(body, box=box.ROUNDED, border_style=self.theme["border"], padding=(1, 3), width=self.width)
        )
        self.status_bar("Press a number key to select")

        return self._read_choice([str(i) for i in range(1, 9)])

    def prompt_player_name(self, current: str) -> str:
        # The one place free text is genuinely required, so this keeps
        # the standard type-and-Enter Prompt rather than single-keypress.
        name = Prompt.ask(f"[{self.theme['secondary']}]Enter player name[/]", default=current)
        return name.strip() or current

    def confirm(self, message: str) -> bool:
        """Single-keypress yes/no confirmation: press 'y' or 'n', no Enter."""
        self.console.print(Align.center(Text(f"{message}  (y/n)", style=f"bold {self.theme['error']}")))
        return self._read_choice(["y", "n"]) == "y"
