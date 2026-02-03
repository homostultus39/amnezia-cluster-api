from fastapi import APIRouter

from src.api.v1.clients.crud import create, read, update, delete

router = APIRouter()

router.include_router(create.router)
router.include_router(read.router)
router.include_router(update.router)
router.include_router(delete.router)