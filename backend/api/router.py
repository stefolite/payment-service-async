from fastapi import APIRouter, Depends

from backend.api.v1.router import v1_router
from backend.core.security import verify_api_key


api_router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

api_router.include_router(v1_router)
