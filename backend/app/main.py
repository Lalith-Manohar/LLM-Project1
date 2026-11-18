"""NEXORA - AI-Powered Retail Management & Intelligence System
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import api_router
from app.schemas.forecast import ReadinessResponse, ComponentReadiness
from app.services.prediction_service import prediction_service
from app.services.historical_data_service import historical_data_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: independently initializes ML models and historical dataset."""
    print("[NEXORA Startup] Initializing application lifespan...")

    # 1. Independent ML model loading & verification
    try:
        prediction_service.load_models()
    except Exception as e:
        print(f"[NEXORA Startup ERROR] ML model initialization failed: {e}")

    # 2. Independent historical demand dataset indexing & schema validation
    try:
        historical_data_service.load_dataset()
    except Exception as e:
        print(f"[NEXORA Startup ERROR] Historical dataset initialization failed: {e}")

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


@app.get("/health", tags=["General"], summary="Liveness check endpoint")
def health_check():
    """Service liveness check indicating that the FastAPI process is active.
    
    Returns 200 OK as long as the HTTP process is alive and responsive.
    Does not imply that machine learning models or inference datasets are loaded.
    """
    return {
        "status": "healthy",
        "service": "backend",
        "version": settings.VERSION
    }


@app.get(
    "/ready",
    response_model=ReadinessResponse,
    tags=["General"],
    summary="Readiness check endpoint",
    responses={
        200: {"description": "All inference services are ready"},
        503: {"description": "One or more critical inference subsystems are not ready"}
    }
)
def readiness_check(response: Response) -> ReadinessResponse:
    """Service readiness probe verifying that ML models and historical datasets are ready.
    
    Returns HTTP 200 when all models are verified and dataset is indexed.
    Returns HTTP 503 Service Unavailable if any component is missing or failed to initialize.
    """
    models_status = prediction_service.get_status()
    data_status = historical_data_service.get_status()

    is_ready = bool(models_status["ready"] and data_status["ready"])
    
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            service="backend",
            version=settings.VERSION,
            models=ComponentReadiness(**models_status),
            historical_data=ComponentReadiness(**data_status)
        )

    return ReadinessResponse(
        status="ready",
        service="backend",
        version=settings.VERSION,
        models=ComponentReadiness(**models_status),
        historical_data=ComponentReadiness(**data_status)
    )


# API v1 route aliases for consistency
@app.get(f"{settings.API_V1_STR}/health", include_in_schema=False)
def api_v1_health():
    return health_check()


@app.get(f"{settings.API_V1_STR}/ready", include_in_schema=False)
def api_v1_ready(response: Response):
    return readiness_check(response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
