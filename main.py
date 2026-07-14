#!/usr/bin/env python3
"""
Typing Speed Pro
-----------------
Entry point for the application. Run with:

    python main.py

See README.md for full setup and usage instructions.
"""

import sys

from src.game import Game


def main() -> None:
    try:
        Game().run()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print(f"\nA fatal error occurred: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
