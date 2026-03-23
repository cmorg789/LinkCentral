"""CLI entry point for scriptlink utilities.

Usage:
    python -m app.scriptlink test PARAM fixture.json [--verbose]
"""
import argparse
import sys

from app.scriptlink.test import main as run_test


def main():
    parser = argparse.ArgumentParser(
        prog="python -m app.scriptlink",
        description="ScriptLink utilities",
    )
    subparsers = parser.add_subparsers(dest="command")

    # test
    test_parser = subparsers.add_parser(
        "test",
        help="Test a script with a JSON fixture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  python -m app.scriptlink test ADMIT fixture.json\n'
            '  python -m app.scriptlink test ADMIT "data/missing scripts/ADMIT.json"\n'
            '  python -m app.scriptlink test "MY PARAM" fixture.json --verbose'
        ),
    )
    test_parser.add_argument(
        "parameter", help="Script parameter name (filename without .py)"
    )
    test_parser.add_argument("fixture", help="Path to JSON fixture file")
    test_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show script print() output"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "test":
        run_test(args)


if __name__ == "__main__":
    main()
