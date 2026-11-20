"""API routes module initialization."""

from fastapi import APIRouter
from app.api.routes import forecast
from app.api.routes import experimental_forecast

api_router = APIRouter()
api_router.include_router(forecast.router)
api_router.include_router(experimental_forecast.router)
