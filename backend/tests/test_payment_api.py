from httpx import ASGITransport, AsyncClient
from backend.main import app
import pytest
from backend.db.session import get_async_session
from uuid import uuid4
from backend.outbox.models import Outbox
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
import asyncio


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


@pytest.mark.asyncio
async def test_create_payment_idempotency(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            payment_data = {
                "amount": 1000,
                "currency": "RUB",
                "description": "description",
                "metadata": {"metadata": "metadata"},
                "webhook_url": "http://test",
            }
            headers = {"Idempotency-Key": str(uuid4())}

            post_response_1 = await client.post(
                "/api/v1/payments",
                json=payment_data,
                headers=headers
            )

            assert post_response_1.status_code == 202

            post_response_2 = await client.post(
                "/api/v1/payments",
                json=payment_data,
                headers=headers
            )

            assert post_response_2.status_code == 202
            assert (
                post_response_2.json()["payment_id"]
                == post_response_1.json()["payment_id"]
            )

            stmt = (
                select(Outbox)
                .where(
                    Outbox.event_type == "payment.created",
                    Outbox.payload["payment_id"].astext
                    == post_response_1.json()["payment_id"]
                )
            )
            result = await test_session.scalars(stmt)
            events = result.all()

            assert len(events) == 1

    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_create_payment_idempotency_conflict(test_session):
    async def override_get_async_session():
        yield test_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            payment_data = {
                "amount": 1000,
                "currency": "RUB",
                "description": "description",
                "metadata": {"metadata": "metadata"},
                "webhook_url": "http://test",
            }
            headers = {"Idempotency-Key": str(uuid4())}

            post_response_1 = await client.post(
                "/api/v1/payments",
                json=payment_data,
                headers=headers
            )

            assert post_response_1.status_code == 202

            payment_data["amount"] = 5000
            post_response_2 = await client.post(
                "/api/v1/payments",
                json=payment_data,
                headers=headers
            )

            assert post_response_2.status_code == 409

    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_create_payment_concurrently(test_engine, test_session):
    async_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False
    )

    async def override_get_async_session():
        async with async_factory() as session:
            yield session

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

            response_1, response_2 = await asyncio.gather(
                client.post(
                    "/api/v1/payments",
                    json=payment_data,
                    headers=headers,
                ),
                client.post(
                    "/api/v1/payments",
                    json=payment_data,
                    headers=headers,
                )
            )

            assert response_1.status_code == 202
            assert response_2.status_code == 202
            assert (
                response_1.json()["payment_id"]
                == response_2.json()["payment_id"]
            )

    finally:
        app.dependency_overrides.pop(get_async_session, None)
