"""Command-line interface for administration tasks."""
import argparse
import getpass
import sys

from app.database.connection import SessionLocal, init_db
from app.database.models import User
from app.api.auth import hash_password


def create_user(username: str, password: str = None):
    """Create a new user.

    Args:
        username: The username for the new user
        password: The password (will prompt if not provided)
    """
    init_db()
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"Error: User '{username}' already exists.")
            sys.exit(1)

        # Get password if not provided
        if not password:
            password = getpass.getpass("Enter password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: Passwords do not match.")
                sys.exit(1)

        if len(password) < 8:
            print("Error: Password must be at least 8 characters.")
            sys.exit(1)

        # Create user
        user = User(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"User '{username}' created successfully.")
    finally:
        db.close()


def reset_password(username: str, password: str = None):
    """Reset a user's password.

    Args:
        username: The username to reset
        password: The new password (will prompt if not provided)
    """
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            sys.exit(1)

        if not password:
            password = getpass.getpass("Enter new password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: Passwords do not match.")
                sys.exit(1)

        if len(password) < 8:
            print("Error: Password must be at least 8 characters.")
            sys.exit(1)

        user.password_hash = hash_password(password)
        db.commit()
        print(f"Password reset for user '{username}'.")
    finally:
        db.close()


def list_users():
    """List all users."""
    init_db()
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No users found.")
            return

        print(f"{'Username':<20} {'Active':<8} {'Last Login':<20}")
        print("-" * 48)
        for user in users:
            last_login = user.last_login.isoformat() if user.last_login else "Never"
            print(f"{user.username:<20} {str(user.is_active):<8} {last_login:<20}")
    finally:
        db.close()


def deactivate_user(username: str):
    """Deactivate a user account.

    Args:
        username: The username to deactivate
    """
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            sys.exit(1)

        if not user.is_active:
            print(f"User '{username}' is already inactive.")
            return

        user.is_active = False
        db.commit()
        print(f"User '{username}' has been deactivated.")
    finally:
        db.close()


def activate_user(username: str):
    """Activate a user account.

    Args:
        username: The username to activate
    """
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            sys.exit(1)

        if user.is_active:
            print(f"User '{username}' is already active.")
            return

        user.is_active = True
        db.commit()
        print(f"User '{username}' has been activated.")
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ScriptLink Workflow Engine CLI",
        prog="python -m app.cli",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-user command
    create_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_parser.add_argument("username", help="Username for the new user")
    create_parser.add_argument(
        "--password", "-p", help="Password (will prompt if not provided)"
    )

    # reset-password command
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("username", help="Username to reset")
    reset_parser.add_argument(
        "--password", "-p", help="New password (will prompt if not provided)"
    )

    # list-users command
    subparsers.add_parser("list-users", help="List all users")

    # deactivate-user command
    deactivate_parser = subparsers.add_parser(
        "deactivate-user", help="Deactivate a user account"
    )
    deactivate_parser.add_argument("username", help="Username to deactivate")

    # activate-user command
    activate_parser = subparsers.add_parser(
        "activate-user", help="Activate a user account"
    )
    activate_parser.add_argument("username", help="Username to activate")

    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.username, args.password)
    elif args.command == "reset-password":
        reset_password(args.username, args.password)
    elif args.command == "list-users":
        list_users()
    elif args.command == "deactivate-user":
        deactivate_user(args.username)
    elif args.command == "activate-user":
        activate_user(args.username)


if __name__ == "__main__":
    main()
