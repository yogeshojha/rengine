from fastapi import APIRouter

from app.api.v1 import auth, users

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
