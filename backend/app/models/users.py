from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class User(CreatedAt, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    target_band: Mapped[float] = mapped_column(Numeric(2, 1, asdecimal=False), default=7.0)
    monthly_ai_budget_usd: Mapped[float] = mapped_column(Numeric(8, 2, asdecimal=False))
