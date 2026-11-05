import pytest
import httpx
from unittest.mock import AsyncMock, Mock
from backend.payments.models import Payment
from sqlalchemy.ext.asyncio import async_sessionmaker
from backend.payments.worker import process_payment


@pytest.mark.parametrize(
    "random_value, expected_status",
    [
        (0.5, "succeeded"),
        (0.95, "failed"),
    ],
)
@pytest.mark.asyncio
async def test_process_payment_idempotency(
    test_session,
    monkeypatch,
    random_value,
    expected_status,
):

    random_mock = Mock(return_value=random_value)

    monkeypatch.setattr(
        "backend.payments.worker.random.random",
        random_mock,
    )

    monkeypatch.setattr(
        "backend.payments.worker.asyncio.sleep",
        AsyncMock(),
    )

    payment_data = {
        "amount": 1000,
        "currency": "RUB",
        "description": "description",
        "_metadata": {"metadata": "metadata"},
        "webhook_url": "http://test",
        "idempotency_key": f"test-payment-{expected_status}",
    }
    payment = Payment(**payment_data)

    test_session.add(payment)
    await test_session.commit()

    test_factory = async_sessionmaker(
        test_session.bind,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        "backend.payments.worker.async_session_factory",
        test_factory,
    )

    response = httpx.Response(
        status_code=200,
        request=httpx.Request("POST", "http://test"),
    )

    http_client = Mock()
    http_client.post = AsyncMock(return_value=response)

    await process_payment(
        {"payment_id": str(payment.id)},
        http_client,
    )

    await test_session.refresh(payment)

    assert payment.status == expected_status
    assert payment.processed_at is not None

    payment_timestamp = payment.processed_at

    await process_payment(
        {"payment_id": str(payment.id)},
        http_client,
    )
    await test_session.refresh(payment)

    assert payment.status == expected_status
    assert payment.processed_at == payment_timestamp
    random_mock.assert_called_once()

    assert http_client.post.await_count == 2

    http_client.post.assert_any_await(
        url="http://test",
        json={
            "payment_id": str(payment.id),
            "status": expected_status,
        },
    )
