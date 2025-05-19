"""
FastAPI Application for MCP Services

This module provides a FastAPI application that serves the MCP services API.
It includes endpoints for reconciliation reporting and other MCP services.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from api.routers.reconciliation import router as reconciliation_router
from api.routers.performance import router as performance_router
from api.routers.notification_preferences import router as notification_preferences_router

# Create FastAPI app
app = FastAPI(
    title="Cryptobot MCP API",
    description="API for Cryptobot MCP Services",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reconciliation_router)
app.include_router(performance_router)
app.include_router(notification_preferences_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Cryptobot MCP API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.environ.get("MCP_API_PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "api_app:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )