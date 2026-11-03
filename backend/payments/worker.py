from backend.core.broker import broker, payment_exchange, payment_queue
from faststream import FastStream
import random
from uuid import UUID
import asyncio
from backend.db.session import async_session_factory
from sqlalchemy import select
from backend.payments.models import Payment
from datetime import datetime, timezone


app = FastStream(broker)

# uv run faststream run backend.payments.worker:app


@broker.subscriber(queue=payment_queue, exchange=payment_exchange)
async def process_payment(data: dict):
    payment_id = UUID(data["payment_id"])

    await asyncio.sleep(random.uniform(2, 5))

    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                select(Payment)
                .where(Payment.id == payment_id)
                .with_for_update()
            )

            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()

            if payment is None:
                raise ValueError(f"Payment {payment_id} not found")

            if payment.status != "pending":
                return None

            payment.status = (
                "succeeded" if random.random() < 0.9 else "failed"
            )
            payment.processed_at = datetime.now(timezone.utc)
