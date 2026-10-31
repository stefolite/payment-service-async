from sqlalchemy.ext.asyncio import AsyncSession
from backend.payments.schemas import PaymentCreate
from backend.payments.models import Payment
from backend.outbox.models import Outbox
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


class IdempotencyConflictError(Exception):
    pass


def payment_matches_data(
    payment: Payment,
    data: PaymentCreate,
) -> bool:
    return (
        payment.amount == data.amount
        and payment.currency == data.currency
        and payment.description == data.description
        and payment._metadata == data.metadata
        and payment.webhook_url == str(data.webhook_url)
    )


async def create_payment(
    session: AsyncSession,
    data: PaymentCreate,
    idempotency_key: str,
) -> Payment:
    """Idempotently creates payment in DB"""
    try:
        async with session.begin():
            stmt = (
                select(Payment)
                .where(Payment.idempotency_key == idempotency_key)
            )
            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()
            if payment is not None:
                if not payment_matches_data(payment, data):
                    raise IdempotencyConflictError()

                return payment

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

    except IntegrityError as exc:
        cause = exc.orig.__cause__

        if (
            getattr(cause, "sqlstate", None) != "23505"
            or getattr(cause, "constraint_name", None)
            != "payments_idempotency_key_key"
        ):
            raise

        async with session.begin():
            stmt = (
                select(Payment)
                .where(Payment.idempotency_key == idempotency_key)
            )
            result = await session.execute(stmt)
            existing_payment = result.scalar_one_or_none()

            if existing_payment is None:
                raise

            if not payment_matches_data(existing_payment, data):
                raise IdempotencyConflictError()

            return existing_payment


async def get_payment(
    session: AsyncSession,
    payment_id: UUID,
) -> Payment | None:
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await session.execute(stmt)

    return result.scalar_one_or_none()
