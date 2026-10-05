"""Reset a user's password from the host: rengine reset-password <username>."""

import argparse
import asyncio
import getpass
import sys
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import async_db_session, engine
from app.core.ratelimit import clear_login_failures, revoke_user_tokens
from app.core.security import hash_password_async
from app.utils.validation import validate_password_strength
from shared.models.user import User
from shared.utils.datetime import utc_now

PROMPT_ATTEMPTS = 3
NOT_RESET = "Password not reset."


class ResetRefusedError(Exception):
    pass


@dataclass(frozen=True)
class Account:
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    totp_enabled: bool


def _say(text: str, stream=sys.stdout) -> None:
    stream.write(f"{text}\n")


async def find(session: AsyncSession, username: str) -> Account:
    user = await session.scalar(select(User).where(User.username == username))
    if user is not None:
        return Account(
            user.id, user.username, user.email, user.is_active, user.totp_enabled
        )
    names = (
        await session.scalars(
            select(User.username)
            .where(User.is_superuser, User.is_active)
            .order_by(User.username)
        )
    ).all()
    message = f"No user named {username}."
    if names:
        message += f"\nAdministrators: {', '.join(names)}"
    raise ResetRefusedError(message)


def checked(password: str, account: Account) -> str:
    if not password:
        message = "No password entered."
        raise ResetRefusedError(message)
    try:
        return validate_password_strength(
            password, user_inputs=[account.email, account.username]
        )
    except ValueError as exc:
        raise ResetRefusedError(str(exc)) from None


def read_password(account: Account) -> str:
    if not sys.stdin.isatty():
        return checked(sys.stdin.readline().rstrip("\r\n"), account)
    for _ in range(PROMPT_ATTEMPTS):
        password = getpass.getpass("New password: ")
        try:
            checked(password, account)
        except ResetRefusedError as exc:
            _say(str(exc), sys.stderr)
            continue
        if getpass.getpass("Repeat password: ") != password:
            _say("Passwords do not match.", sys.stderr)
            continue
        return password
    raise ResetRefusedError(NOT_RESET)


async def reset(
    session: AsyncSession, account: Account, password: str, *, remove_2fa: bool
) -> bool:
    user = await session.get(User, account.id)
    if user is None:
        message = f"No user named {account.username}."
        raise ResetRefusedError(message)
    user.hashed_password = await hash_password_async(password)
    if remove_2fa:
        user.totp_secret_encrypted = None
        user.totp_enabled = False
        user.totp_backup_codes = None
    user.updated_at = utc_now()
    session.add(user)
    await session.commit()
    signed_out = await revoke_user_tokens(user.id)
    return await clear_login_failures(user.username) and signed_out


def report(account: Account, *, signed_out: bool, remove_2fa: bool) -> list[str]:
    lines = [f"Password reset for {account.username}."]
    if remove_2fa and account.totp_enabled:
        lines.append("Two-factor authentication removed.")
    elif account.totp_enabled:
        lines.append("Two-factor authentication is on.")
    if signed_out:
        lines.append("Sessions signed out.")
    else:
        lines.append(
            "Sessions not signed out. Check that the redis service is running, "
            "then run reset-password again."
        )
    if not account.is_active:
        lines.append(f"{account.username} is disabled. Enable it in Settings, Users.")
    return lines


async def run(username: str, *, remove_2fa: bool) -> int:
    try:
        async with async_db_session() as session:
            account = await find(session, username)
        password = read_password(account)
        async with async_db_session() as session:
            signed_out = await reset(session, account, password, remove_2fa=remove_2fa)
    except ResetRefusedError as exc:
        _say(str(exc), sys.stderr)
        return 1
    finally:
        await engine.dispose()
    _say("\n".join(report(account, signed_out=signed_out, remove_2fa=remove_2fa)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="rengine reset-password")
    parser.add_argument("username")
    parser.add_argument(
        "--remove-2fa",
        action="store_true",
        help="remove two-factor authentication from the account",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.username, remove_2fa=args.remove_2fa))
    except (KeyboardInterrupt, EOFError):
        _say(f"\n{NOT_RESET}", sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
