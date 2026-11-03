from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.outbox.models import Outbox
from backend.core.broker import broker, payment_exchange
from datetime import datetime, timezone
import asyncio
from backend.db.session import async_session_factory
import logging


logger = logging.getLogger(__name__)


async def publish_batch(session: AsyncSession) -> int:
    stmt = (
        select(Outbox)
        .where(Outbox.published_at.is_(None))
        .order_by(Outbox.created_at)
        .limit(50)
        .with_for_update(skip_locked=True)
    )

    async with session.begin():
        events = (await session.scalars(stmt)).all()

        for event in events:
            await broker.publish(
                message=event.payload,
                exchange=payment_exchange,
                routing_key=event.event_type,
                persist=True,
            )

            event.published_at = datetime.now(timezone.utc)

    return len(events)


async def main():
    async with broker:
        while True:
            async with async_session_factory() as session:
                try:
                    print(await publish_batch(session))
                except Exception:
                    logger.exception("Outbox publication failed")

            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())

# uv run python -m backend.outbox.publisher
