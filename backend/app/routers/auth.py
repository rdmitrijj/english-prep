from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import users as users_repo
from app.schemas.auth import LoginIn, UserOut
from app.security import COOKIE_NAME, CurrentUser, check_login_rate, hash_password, set_session_cookie, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Verifying against a dummy hash when the email is unknown keeps response time the same,
# so an attacker can't tell which emails exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, request: Request, response: Response, session: Annotated[AsyncSession, Depends(get_session)]):
    # ponytail: behind Render's proxy every client shares one host, so this is a global 5/min login limit;
    # key on the proxy's client IP header if there are ever more than a handful of users.
    check_login_rate(request.client.host if request.client else "unknown")
    user = await users_repo.get_by_email(session, body.email)
    if not verify_password(body.password, user.password_hash if user else _DUMMY_HASH) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
