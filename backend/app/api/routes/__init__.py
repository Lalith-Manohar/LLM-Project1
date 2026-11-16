"""API routes module initialization."""

from fastapi import APIRouter
from app.api.routes import forecast

api_router = APIRouter()
api_router.include_router(forecast.router)
