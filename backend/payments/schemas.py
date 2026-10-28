from pydantic import BaseModel, Field, JsonValue, HttpUrl
from decimal import Decimal
from typing import Literal
from uuid import UUID
from datetime import datetime


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Literal["RUB", "USD", "EUR"]
    description: str = Field(max_length=128)
    metadata: dict[str, JsonValue]
    webhook_url: HttpUrl


class PaymentAccepted(BaseModel):
    payment_id: UUID
    status: Literal["pending"]
    created_at: datetime
