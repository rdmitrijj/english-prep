from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


async def create(session: AsyncSession, *, email: str, password_hash: str, display_name: str, budget_usd: float) -> User:
    user = User(email=email.lower(), password_hash=password_hash, display_name=display_name, monthly_ai_budget_usd=budget_usd)
    session.add(user)
    await session.commit()
    return user
