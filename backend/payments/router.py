from fastapi import APIRouter, Header, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_session
from backend.payments.schemas import PaymentCreate, PaymentAccepted
from backend.payments.service import create_payment


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
