from sqlalchemy.ext.asyncio import AsyncSession
from backend.payments.schemas import PaymentCreate
from backend.payments.models import Payment
from backend.outbox.models import Outbox


async def create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    async with session.begin():
        payment = Payment(
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            _metadata=data.metadata,
            webhook_url=str(data.webhook_url),
            idempotency_key=idempotency_key
        )
        session.add(payment)
        await session.flush()

        event = Outbox(
            event_type="payment.created",
            payload={"payment_id": str(payment.id)}
        )
        session.add(event)

    return payment
