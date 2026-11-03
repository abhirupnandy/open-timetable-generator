"""Create a user or reset a password from the command line.

    uv run python -m app.manage_users create admin2 --role ADMIN
    uv run python -m app.manage_users reset-password admin
    uv run python -m app.manage_users list

Useful when nobody can sign in any more. The password is prompted for.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.api.v1.auth import find_user
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal


def _password() -> str:
    first = getpass.getpass("Password (min 8 characters): ")
    if len(first) < 8 or first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords must match and be at least 8 characters.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a user")
    create.add_argument("username")
    create.add_argument("--role", choices=[role.value for role in UserRole], default="ADMIN")
    create.add_argument("--faculty", help="employee ID (required for FACULTY)")
    create.add_argument("--name", default="")
    reset = commands.add_parser("reset-password", help="set a new password")
    reset.add_argument("username")
    commands.add_parser("list", help="list users")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        if args.command == "list":
            for user in db.scalars(select(User).order_by(User.username)):
                state = "" if user.is_active else " (inactive)"
                link = f" -> {user.faculty_employee_id}" if user.faculty_employee_id else ""
                print(f"{user.username:<24} {user.role.value:<12}{link}{state}")
            return 0

        user = find_user(db, args.username)
        now = datetime.now(UTC)

        if args.command == "create":
            if user is not None:
                sys.exit(f"User {args.username} already exists.")
            if args.role == UserRole.FACULTY and not args.faculty:
                sys.exit("FACULTY users need --faculty <employee ID>.")
            db.add(
                User(
                    username=args.username,
                    full_name=args.name,
                    password_hash=hash_password(_password()),
                    role=UserRole(args.role),
                    faculty_employee_id=args.faculty,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            if user is None:
                sys.exit(f"No user {args.username}.")
            user.password_hash = hash_password(_password())
            user.is_active = True
            user.updated_at = now
        db.commit()
        print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
