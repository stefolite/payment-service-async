import pytest
from unittest.mock import AsyncMock

from backend.outbox.models import Outbox
from backend.outbox.publisher import publish_batch, broker


@pytest.mark.asyncio
async def test_publish_batch_success(test_session, monkeypatch):
    event = Outbox(
        event_type="payment.created",
        payload={"payment_id": "test_payment_id"},
    )

    test_session.add(event)
    await test_session.commit()

    mock_publish = AsyncMock()
    monkeypatch.setattr(broker, "publish", mock_publish)

    count = await publish_batch(test_session)

    assert count == 1

    mock_publish.assert_awaited_once()
    await test_session.refresh(event)

    assert event.published_at is not None


@pytest.mark.asyncio
async def test_publish_batch_failure(test_session, monkeypatch):
    event = Outbox(
        event_type="payment.created",
        payload={"payment_id": "test_payment_id"},
    )

    test_session.add(event)
    await test_session.commit()

    mock_publish = AsyncMock(
        side_effect=ConnectionError("RabbitMQ unavailable")
    )
    monkeypatch.setattr(broker, "publish", mock_publish)

    with pytest.raises(ConnectionError):
        await publish_batch(test_session)

    mock_publish.assert_awaited_once()

    await test_session.refresh(event)

    assert event.published_at is None
