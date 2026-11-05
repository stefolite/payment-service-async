
import pytest
import httpx
from unittest.mock import AsyncMock, Mock, call
from backend.webhooks.service import deliver_webhook


@pytest.mark.asyncio
async def test_deliver_webhook_retry_exhausted(monkeypatch):
    mock_sleep = AsyncMock()

    monkeypatch.setattr(
        "backend.webhooks.service.asyncio.sleep",
        mock_sleep,
    )

    response = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "http://test"),
    )

    http_client = Mock()
    http_client.post = AsyncMock(return_value=response)

    with pytest.raises(httpx.HTTPStatusError):
        await deliver_webhook(
            http_client,
            "http://test",
            {"payment_id": "123", "status": "succeeded"},
        )

    assert http_client.post.await_count == 3
    assert mock_sleep.await_args_list == [call(1), call(2)]


@pytest.mark.asyncio
async def test_deliver_webhook_success():
    requests_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests_count
        requests_count += 1
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        await deliver_webhook(
            client,
            "https://example.com/webhook",
            {"payment_id": "123", "status": "succeeded"},
        )

    assert requests_count == 1


@pytest.mark.asyncio
async def test_deliver_webhook_retry_success(monkeypatch):
    sleep_mock = AsyncMock()

    monkeypatch.setattr(
        "backend.webhooks.service.asyncio.sleep",
        sleep_mock,
    )

    requests_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests_count
        requests_count += 1

        if requests_count < 3:
            return httpx.Response(500)

        return httpx.Response(200)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        await deliver_webhook(
            client,
            "https://example.com/webhook",
            {"payment_id": "123", "status": "succeeded"},
        )

    assert requests_count == 3
    assert sleep_mock.await_args_list == [call(1), call(2)]
