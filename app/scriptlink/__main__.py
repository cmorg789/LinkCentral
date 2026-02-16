"""CLI entry point for scriptlink utilities.

Usage:
    python -m app.scriptlink test PARAM fixture.json [--verbose]
    python -m app.scriptlink encrypt-password [--secret-key KEY]
"""
import argparse
import getpass
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

    # encrypt-password
    ep_parser = subparsers.add_parser(
        "encrypt-password", help="Encrypt a password for connections.yaml"
    )
    ep_parser.add_argument(
        "--secret-key",
        help="SECRET_KEY to use for encryption (if not set in .env or environment)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "test":
        run_test(args)
    elif args.command == "encrypt-password":
        encrypt_password(args)


def encrypt_password(args):
    from app.scriptlink.connections import encrypt_password as _encrypt

    password = getpass.getpass("Password to encrypt: ")
    if not password:
        print("Error: Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    try:
        encrypted = _encrypt(password, secret_key=args.secret_key)
    except Exception as e:
        print(
            f"Error: {e}\n"
            "Use --secret-key to provide it directly:\n"
            "  python -m app.scriptlink encrypt-password --secret-key YOUR_KEY",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nEncrypted password:\n{encrypted}")
    print("\nAdd this to connections.yaml as password_encrypted.")


if __name__ == "__main__":
    main()
