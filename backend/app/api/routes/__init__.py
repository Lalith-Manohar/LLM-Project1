"""API routes module initialization."""

from fastapi import APIRouter
from app.api.routes import categories
from app.api.routes import forecast
from app.api.routes import experimental_forecast
from app.api.routes import inventory
from app.api.routes import products

api_router = APIRouter()
api_router.include_router(forecast.router)
api_router.include_router(experimental_forecast.router)
api_router.include_router(inventory.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
