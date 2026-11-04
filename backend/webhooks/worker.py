# faststream run backend.webhooks.worker:app


from faststream import FastStream, Context, ContextRepo, AckPolicy
from backend.core.broker import (
    broker,
    payment_exchange,
    webhook_queue,
    webhook_dlq,
    webhook_dlx,
)
from uuid import UUID
from backend.db.session import async_session_factory
from sqlalchemy import select
from backend.payments.models import Payment
from contextlib import asynccontextmanager
import httpx
import asyncio


@asynccontextmanager
async def lifespan(context: ContextRepo):
    async with httpx.AsyncClient(timeout=10.0) as client:
        context.set_global("http_client", client)
        yield


app = FastStream(broker, lifespan=lifespan)


@broker.subscriber(
        queue=webhook_queue,
        exchange=payment_exchange,
        ack_policy=AckPolicy.REJECT_ON_ERROR,
)
async def process_webhook(
    data: dict,
    http_client: httpx.AsyncClient = Context(),
):
    payment_id = UUID(data["payment_id"])

    async with async_session_factory() as session:
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        webhook_url = payment.webhook_url
        payload = {
            "payment_id": str(payment.id),
            "status": payment.status,
        }

    for attempt in range(3):
        try:
            response = await http_client.post(
                url=webhook_url,
                json=payload,
            )
            response.raise_for_status()
            return None

        except httpx.HTTPError:
            if attempt == 2:
                raise

            await asyncio.sleep(2 ** attempt)


@app.after_startup
async def setup_dlq():
    exchange = await broker.declare_exchange(webhook_dlx)
    queue = await broker.declare_queue(webhook_dlq)
    await queue.bind(exchange, routing_key="webhook.failed")
