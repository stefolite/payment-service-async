from backend.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Numeric, CheckConstraint, DateTime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')",
            name="ck_payments_status"
        ),
        default="pending"
    )
    description: Mapped[str] = mapped_column(String(128))
    webhook_url: Mapped[str]
    _metadata: Mapped[dict] = mapped_column(JSONB, name="metadata")
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
