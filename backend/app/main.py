"""NEXORA - AI-Powered Retail Management & Intelligence System
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API services for demand forecasting, inventory management, and retail intelligence.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware setup for future React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production
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
