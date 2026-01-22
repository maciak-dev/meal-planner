from fastapi import APIRouter
from app.api.v1.recipes import router as recipes_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(recipes_router, prefix="/recipes", tags=["recipes"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
