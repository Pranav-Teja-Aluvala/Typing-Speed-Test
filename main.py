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
