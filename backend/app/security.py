"""Password hashing (Argon2), JWT session cookie, and the `current_user` dependency."""

import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models.users import User
from app.repositories import users as users_repo

COOKIE_NAME = "session"
_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def create_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(days=s.jwt_ttl_days)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.jwt_secret, algorithm="HS256")


def set_session_cookie(response: Response, user_id: int) -> None:
    s = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id),
        max_age=s.jwt_ttl_days * 86400,
        httponly=True,  # JavaScript cannot read it → XSS cannot steal it
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
    )


async def current_user(request: Request, session: Annotated[AsyncSession, Depends(get_session)]) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise unauthorized
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise unauthorized
    user = await users_repo.get_by_id(session, int(payload["sub"]))
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(current_user)]

# ponytail: in-memory per-IP login throttle; fine for one instance, move to the DB if we ever scale out.
_LOGIN_LIMIT, _LOGIN_WINDOW_S = 5, 60
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def check_login_rate(ip: str) -> None:
    now = time.monotonic()
    hits = _login_attempts[ip]
    while hits and now - hits[0] > _LOGIN_WINDOW_S:
        hits.popleft()
    if len(hits) >= _LOGIN_LIMIT:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts, wait a minute")
    hits.append(now)
