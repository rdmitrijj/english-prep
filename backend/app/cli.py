"""Admin commands. There is no public sign-up: users are created here.

    docker compose exec backend python -m app.cli create-user --email you@example.com --name "Your Name"
"""

import argparse
import asyncio
import getpass
import sys

from app.config import get_settings
from app.db import SessionLocal
from app.repositories import users as users_repo
from app.security import hash_password


async def create_user(email: str, name: str, password: str) -> None:
    async with SessionLocal() as session:
        if await users_repo.get_by_email(session, email):
            sys.exit(f"User {email} already exists")
        await users_repo.create(
            session,
            email=email,
            password_hash=hash_password(password),
            display_name=name,
            budget_usd=get_settings().default_monthly_ai_budget_usd,
        )
    print(f"Created user {email}")


async def ensure_admin() -> None:
    """Create ADMIN_EMAIL / ADMIN_PASSWORD on start if missing. An existing user is left as is (password included)."""
    s = get_settings()
    if not (s.admin_email and s.admin_password):
        return
    if len(s.admin_password) < 10:
        sys.exit("ADMIN_PASSWORD too short (min 10 chars)")
    async with SessionLocal() as session:
        if await users_repo.get_by_email(session, s.admin_email):
            return
    await create_user(s.admin_email, s.admin_email.split("@")[0], s.admin_password)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cu = sub.add_parser("create-user")
    cu.add_argument("--email", required=True)
    cu.add_argument("--name", required=True)
    sub.add_parser("ensure-admin")
    args = parser.parse_args()

    if args.command == "ensure-admin":
        asyncio.run(ensure_admin())

    if args.command == "create-user":
        password = getpass.getpass("Password (min 10 chars): ")
        if len(password) < 10:
            sys.exit("Password too short")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords do not match")
        asyncio.run(create_user(args.email, args.name, password))


if __name__ == "__main__":
    main()
