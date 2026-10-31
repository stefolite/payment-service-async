from httpx import ASGITransport, AsyncClient
from backend.main import app
import pytest
from backend.db.session import get_async_session
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_and_get_payment(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test"
        ) as client:
            payment_data = {
                "amount": 1000,
                "currency": "RUB",
                "description": "description",
                "metadata": {"metadata": "metadata"},
                "webhook_url": "http://test",
            }
            headers = {"Idempotency-Key": str(uuid4())}

            post_response = await client.post(
                "/api/v1/payments",
                json=payment_data,
                headers=headers
            )

            assert post_response.status_code == 202

            post_response_data = post_response.json()
            payment_id = post_response_data["payment_id"]

            assert payment_id is not None
            assert post_response_data["status"] == "pending"

            get_response = await client.get(
                f"/api/v1/payments/{payment_id}"
            )

            assert get_response.status_code == 200

            get_response_data = get_response.json()

            assert get_response_data["payment_id"] == payment_id
            assert get_response_data["status"] == "pending"

    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_get_payment_not_found(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test"
        ) as client:
            payment_id = str(uuid4())
            get_response = await client.get(
                f"/api/v1/payments/{payment_id}"
            )

            assert get_response.status_code == 404
            assert get_response.json()["detail"] == "Payment not found"

    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_create_payment_without_idempotency_key(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test"
        ) as client:
            payment_data = {
                "amount": 1000,
                "currency": "RUB",
                "description": "description",
                "metadata": {"metadata": "metadata"},
                "webhook_url": "http://test",
            }

            post_response = await client.post(
                "/api/v1/payments",
                json=payment_data,
            )

            assert post_response.status_code == 422

    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_get_payment_invalid_uuid(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test"
        ) as client:
            get_response = await client.get(
                "/api/v1/payments/invalid_uuid"
            )

            assert get_response.status_code == 422

    finally:
        app.dependency_overrides.pop(get_async_session, None)
