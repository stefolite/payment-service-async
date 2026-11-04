import pytest
import httpx
from unittest.mock import AsyncMock, Mock, call
from sqlalchemy.ext.asyncio import async_sessionmaker
from backend.payments.models import Payment
from backend.webhooks.worker import process_webhook
from uuid import uuid4


@pytest.mark.asyncio
async def test_webhook_success(test_session, monkeypatch):
    payment_data = {
        "amount": 1000,
        "currency": "RUB",
        "status": "succeeded",
        "description": "description",
        "_metadata": {"metadata": "metadata"},
        "webhook_url": "http://test",
        "idempotency_key": str(uuid4()),
    }
    payment = Payment(**payment_data)

    test_session.add(payment)
    await test_session.commit()

    test_factory = async_sessionmaker(
        test_session.bind,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        "backend.webhooks.worker.async_session_factory",
        test_factory,
    )

    response = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", "http://test")
    )

    http_client = Mock()
    http_client.post = AsyncMock(return_value=response)

    await process_webhook(
        {"payment_id": str(payment.id)},
        http_client,
    )

    http_client.post.assert_awaited_once_with(
        url="http://test",
        json={
            "payment_id": str(payment.id),
            "status": "succeeded"
        }
    )


@pytest.mark.asyncio
async def test_webhook_retry(test_session, monkeypatch):
    payment_data = {
        "amount": 1000,
        "currency": "RUB",
        "status": "succeeded",
        "description": "description",
        "_metadata": {"metadata": "metadata"},
        "webhook_url": "http://test",
        "idempotency_key": str(uuid4()),
    }
    payment = Payment(**payment_data)

    test_session.add(payment)
    await test_session.commit()

    test_factory = async_sessionmaker(
        test_session.bind,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        "backend.webhooks.worker.async_session_factory",
        test_factory,
    )

    response = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "http://test"),
    )

    http_client = Mock()
    http_client.post = AsyncMock(return_value=response)

    mock_sleep = AsyncMock()

    monkeypatch.setattr(
        "backend.webhooks.worker.asyncio.sleep",
        mock_sleep,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await process_webhook(
            {"payment_id": str(payment.id)},
            http_client,
        )

    assert http_client.post.await_count == 3

    mock_sleep.assert_has_awaits([call(1), call(2)])
    assert mock_sleep.await_count == 2
