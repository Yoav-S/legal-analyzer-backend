"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logger import setup_logger
from app.utils.errors import AppException
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes import (
    auth,
    upload,
    analyze,
    reports,
    billing,
    users,
    documents,
    status,
)

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 CreativeDoc Backend starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"MongoDB: {settings.MONGODB_DB_NAME}")
    logger.info(f"Storage: {settings.STORAGE_TYPE}")
    
    yield
    
    # Shutdown
    logger.info("👋 CreativeDoc Backend shutting down...")


# Create FastAPI app
app = FastAPI(
    title="CreativeDoc API",
    description="AI-Powered Legal Document Analyzer Backend",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
if settings.ENVIRONMENT == "production":
    app.add_middleware(RateLimitMiddleware)


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.DEBUG else None,
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(upload.router, prefix="/documents", tags=["Documents"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(status.router, prefix="/documents", tags=["Documents"])
app.include_router(analyze.router, prefix="/documents", tags=["Analysis"])
app.include_router(reports.router, prefix="/documents", tags=["Reports"])
app.include_router(billing.router, prefix="/billing", tags=["Billing"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )

