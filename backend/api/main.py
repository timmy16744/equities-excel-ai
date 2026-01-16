"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import router as api_router
from backend.api.settings_routes import router as settings_router
from backend.api.websocket import router as ws_router
from backend.api.auth_routes import router as auth_router
from backend.api.health_routes import router as health_router
from backend.utils.logging import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    logger.info("Starting Equities AI API")
    yield
    logger.info("Shutting down Equities AI API")


app = FastAPI(
    title="Equities AI Analysis Platform",
    description="Multi-agent AI system for equity market analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "Equities AI Analysis Platform",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(api_router, prefix="/api", tags=["analysis"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])
