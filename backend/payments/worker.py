# faststream run backend.payments.worker:app


from backend.core.broker import (
    broker,
    payment_exchange,
    payment_queue,
    webhook_dlq,
    webhook_dlx,
)
from faststream import FastStream, Context, ContextRepo, AckPolicy
import random
from uuid import UUID
import asyncio
from backend.db.session import async_session_factory
from sqlalchemy import select
from backend.payments.models import Payment
from backend.webhooks.service import deliver_webhook
from datetime import datetime, timezone
import httpx
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(context: ContextRepo):
    async with httpx.AsyncClient(timeout=10.0) as client:
        context.set_global("http_client", client)
        yield


app = FastStream(broker, lifespan=lifespan)


@broker.subscriber(
    queue=payment_queue,
    exchange=payment_exchange,
    ack_policy=AckPolicy.REJECT_ON_ERROR,
)
async def process_payment(
    data: dict,
    http_client: httpx.AsyncClient = Context(),
):
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

            if payment.status == "pending":
                payment.status = (
                    "succeeded" if random.random() < 0.9 else "failed"
                )
                payment.processed_at = datetime.now(timezone.utc)

            webhook_url = payment.webhook_url
            payload = {
                "payment_id": str(payment.id),
                "status": payment.status,
            }

    await deliver_webhook(http_client, webhook_url, payload)


@app.after_startup
async def setup_dlq():
    exchange = await broker.declare_exchange(webhook_dlx)
    queue = await broker.declare_queue(webhook_dlq)
    await queue.bind(exchange, routing_key="webhook.failed")
