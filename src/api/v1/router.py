from fastapi import APIRouter

from src.api.v1.endpoints.applications import router as applications_router

router = APIRouter()


@router.get("/ping")
async def ping():
    return {"ping": "pong"}


router.include_router(applications_router)
