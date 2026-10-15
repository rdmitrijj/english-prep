from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.content import Test
from app.models.enums import ContentStatus, TestKind
from app.routers.attempts import Session, shown_seconds
from app.schemas.attempts import TestOut, TestSectionOut
from app.security import CurrentUser

router = APIRouter(tags=["content"])


@router.get("/tests", response_model=list[TestOut])
async def list_mock_tests(user: CurrentUser, session: Session):
    """Published mock tests, for the "start a mock" page. Practice content has its own endpoints (M4)."""
    tests = await session.scalars(
        select(Test).options(selectinload(Test.sections))
        .where(Test.kind == TestKind.mock, Test.status == ContentStatus.published).order_by(Test.slug)
    )
    return [TestOut(id=t.id, title=t.title, sections=[
        TestSectionOut(skill=s.skill, duration_s=await shown_seconds(session, s)) for s in t.sections
    ]) for t in tests]
