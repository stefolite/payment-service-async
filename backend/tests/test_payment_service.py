from backend.payments.schemas import PaymentCreate
from backend.payments.service import create_payment
from sqlalchemy import select
from backend.payments.models import Payment
from backend.outbox.models import Outbox
import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_payment(test_session):
    payment_data = PaymentCreate(
        amount=1000,
        currency="RUB",
        description="description",
        metadata={"metadata": "metadata"},
        webhook_url="http://test.com"
    )
    idempotency_key = str(uuid4())
    payment = await create_payment(
        test_session,
        payment_data,
        idempotency_key
    )

    assert payment.id is not None
    assert payment.status == "pending"

    stmt = select(Payment).where(Payment.id == payment.id)
    result = await test_session.execute(stmt)
    saved_payment = result.scalar_one()

    assert saved_payment.id == payment.id

    result = await test_session.scalars(select(Outbox))
    events = result.all()
    event = [
        event for event in events
        if event.event_type == "payment.created"
        and event.payload.get("payment_id") == str(payment.id)
    ]

    assert len(event) == 1
