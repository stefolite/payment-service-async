from fastapi import (
    APIRouter,
    Header,
    Depends,
    status,
    HTTPException
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.db.session import get_async_session
from backend.payments.schemas import (
    PaymentCreate,
    PaymentAccepted,
    PaymentRead
)
from backend.payments.service import create_payment, get_payment


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    response_model=PaymentAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment_endpoint(
    data: PaymentCreate,
    idempotency_key: str = Header(),
    session: AsyncSession = Depends(get_async_session),
):
    payment = await create_payment(session, data, idempotency_key)

    return PaymentAccepted(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentRead,
)
async def get_payment_endpoint(
    payment_id: UUID,
    session: AsyncSession = Depends(get_async_session)
):
    payment = await get_payment(session, payment_id)

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    return PaymentRead(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
