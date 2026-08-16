from fastapi import APIRouter
from app.api.v1.recipes import router as recipes_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.recipe_import import router as recipe_import_router
from app.api.v1.shop import router as shop_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(recipes_router, prefix="/recipes", tags=["recipes"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(recipe_import_router, prefix="/recipe-import", tags=["recipe-import"])
api_router.include_router(shop_router, tags=["shop"])
