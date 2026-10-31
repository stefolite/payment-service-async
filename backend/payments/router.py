from fastapi import APIRouter, Header, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_session
from backend.payments.schemas import PaymentCreate, PaymentAccepted
from backend.payments.service import create_payment


router = APIRouter(prefix="/payments", tags=["payments"])
