"""
Simplified FastAPI application for testing without database
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Simplified version for testing",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running without database"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }

# Include the webhooks router for Twilio at both paths
from app.api.v1.webhooks import router as webhooks_router

# Mount at the expected Twilio path
app.include_router(
    webhooks_router,
    prefix="/twilio",
    tags=["webhooks"]
)

# Also mount at the API path
app.include_router(
    webhooks_router,
    prefix="/api/v1/webhooks",
    tags=["webhooks"]
)

# Include WebSocket router
from app.api.v1.websocket import router as websocket_router
app.include_router(
    websocket_router,
    prefix="/api/v1",
    tags=["websocket"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_simple:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
