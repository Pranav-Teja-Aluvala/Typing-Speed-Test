# Typing Speed Pro

A polished, terminal-based typing speed and accuracy trainer built with
Python and [Rich](https://github.com/Textualize/rich). Think Monkeytype,
but running entirely in your terminal — live colored feedback, WPM/accuracy
tracking, a persistent leaderboard, and long-term statistics.

## Features

- **Live typing test** with a Monkeytype-style HUD: current WPM, accuracy,
  time remaining, mistakes, and characters typed, all updating ~20 times a
  second while you type.
- **Color-coded passage rendering** — correct characters in green,
  incorrect ones underlined in red, the current character highlighted as a
  cursor, and untyped text dimmed.
- **Four difficulty tiers**: Easy, Medium, Hard, and Random Quotes, each
  drawing from its own text bank and shuffled into a fresh passage every
  test.
- **Practice Mode** — untimed, unscored, for pure muscle-memory practice.
- **Local leaderboard** (top 20), sortable by WPM, accuracy, or date.
- **Persistent statistics**: average/highest WPM, average/best accuracy,
  total tests, total typing time, total characters typed, total mistakes,
  and your current/longest daily streak.
- **Settings**: player name, default duration/difficulty, three color
  themes (Midnight Cyan, Sunset Gold, Classic Mono), sound toggle, and
  one-click resets for stats or leaderboard.
- **Cross-platform keyboard input** — a single `KeyReader` abstraction
  handles non-blocking single-key reads on both Windows (`msvcrt`) and
  POSIX (`termios`/`tty`/`select`) without any third-party dependency.
- **Crash-resistant persistence** — every JSON write is atomic (write to
  a temp file, then replace), and every JSON read tolerates a missing,
  empty, or corrupted file by falling back to safe defaults instead of
  crashing.

## Installation

Requires Python 3.9+.

```bash
git clone <this-repo-url>
cd typing-speed-pro
pip install -r requirements.txt
python main.py
```

That's it — no build step, no external services, no API keys.

## Screenshots

The `screenshots/` folder is included for you to drop in your own terminal
captures (e.g. via `screenshot.sh`, macOS `Cmd+Shift+4`, or your terminal
emulator's built-in tool) once you've run the app locally — a live
terminal UI can't be meaningfully captured as a static image ahead of
time, so none are checked in yet. Suggested shots: the main menu, a live
typing test mid-run, the result screen, and the leaderboard.

## Folder Structure

```
typing-speed-pro/
├── main.py                 # Entry point — run this
├── requirements.txt        # Single dependency: rich
├── README.md
├── assets/                 # Source text banks (plain .txt, one line each)
│   ├── easy.txt
│   ├── medium.txt
│   ├── hard.txt
│   └── quotes.txt
├── data/                   # Persistent JSON state (safe to delete individually)
│   ├── leaderboard.json
│   ├── history.json
│   └── settings.json
├── screenshots/            # Drop your own terminal captures here
└── src/
    ├── __init__.py
    ├── constants.py         # Paths, theme palettes, durations, difficulty config
    ├── utils.py              # JSON persistence, formatting, cross-platform KeyReader
    ├── config.py              # Settings load/save/validate
    ├── paragraphs.py           # Builds shuffled passages from the text banks
    ├── typing.py                # TypingTestEngine — scoring logic, no UI dependency
    ├── leaderboard.py            # Top-20 leaderboard persistence + sorting
    ├── statistics.py              # Lifetime stats + daily streak tracking
    ├── ui.py                       # All Rich rendering (menus, live HUD, reports)
    └── game.py                     # Application controller / main loop
```

**Why this layout?** `typing.py` (scoring) has zero Rich or I/O
dependencies, so it can be unit tested in complete isolation — feed it
key events, read back the numbers. `ui.py` owns all presentation, and
`game.py` is the only module that knows about the overall program flow,
wiring the engine, UI, settings, leaderboard, and statistics together.
Business logic, presentation, and orchestration never bleed into each
other.

## How WPM Is Calculated

Two figures are tracked, matching the convention used by most typing
test sites:

- **Gross WPM** = `(total characters typed / 5) / minutes elapsed`
  The `/ 5` follows the standard convention that one "word" = 5
  characters (including spaces), regardless of actual word length.

- **Net WPM** = `((total characters typed / 5) - (incorrect characters / 5)) / minutes elapsed`,
  floored at 0. This is the headline number shown during the test and on
  the report — it penalizes uncorrected mistakes still present in the
  final input, so leaving errors uncorrected costs you WPM even if you
  typed fast.

- **Accuracy** = `correct characters / total characters typed * 100`,
  based on the final state of your input (corrected mistakes don't count
  against you; only what's on screen when the test ends does).

- **Mistakes** (shown separately) is a *cumulative* counter — every wrong
  keystroke counts once, even if you immediately backspace and fix it.
  This rewards clean typing over "type fast, fix later" strategies while
  still keeping Net WPM based on the final text.

Performance ratings on the report screen are bucketed by Net WPM:

| Net WPM | Rating          |
|---------|-----------------|
| 90+     | Elite Typist    |
| 70–89   | Fast Typist     |
| 50–69   | Intermediate    |
| 30–49   | Beginner        |
| 0–29    | Needs Practice  |

## Architecture

```
KeyReader (utils.py)  ──keystrokes──▶  TypingTestEngine (typing.py)
                                              │
                                              ▼
                                     TestResult (dataclass)
                                              │
                       ┌──────────────────────┼───────────────────────┐
                       ▼                      ▼                       ▼
              Leaderboard.add_score   Statistics.record_test    UI.show_report
              (leaderboard.py)        (statistics.py)           (ui.py)
```

`game.py`'s `Game` class owns the main loop and a single `_run_session()`
method shared by both **Start Test** and **Practice Mode** — the only
difference is a `timed` flag that gates whether the engine's timer ends
the test and whether results are persisted. This avoids duplicating the
entire live-typing loop for two nearly identical flows.

The live view runs inside a `rich.live.Live` context, polling the
keyboard with a short (50ms) timeout each frame so the display can keep
refreshing (timer ticking down, etc.) even between keystrokes.

## Future Improvements

- Multiplayer / race mode over a local socket
- Per-key error heatmap to highlight which keys need practice
- Custom text import (paste your own passage or load a file)
- Configurable sound effects (the setting currently exists but audio
  playback isn't wired up — deliberately left out rather than shipped
  half-working, since terminal beep support is inconsistent across
  platforms)
- Export statistics/leaderboard to CSV

## License

MIT — do whatever you like with it.
