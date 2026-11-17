"""NEXORA - AI-Powered Retail Management & Intelligence System
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import api_router
from app.services.prediction_service import prediction_service
from app.services.historical_data_service import historical_data_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: loads ML models and historical sales data into memory once at startup."""
    print("[NEXORA Startup] Initializing application lifespan...")
    try:
        prediction_service.load_models()
        historical_data_service.load_dataset()
    except Exception as e:
        print(f"[NEXORA Startup Warning] Service loading deferred or encountered an error: {e}")
    yield
    print("[NEXORA Shutdown] Application shutting down cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API services for demand forecasting, inventory management, and retail intelligence.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware setup for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under standard prefix /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["General"], summary="Root endpoint")
def root():
    """Welcome endpoint providing service metadata."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs"
    }


@app.get("/health", tags=["General"], summary="Health check endpoint")
def health_check():
    """Service health check returning uptime and backend status."""
    return {
        "status": "healthy",
        "service": "backend",
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
