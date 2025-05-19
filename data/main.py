from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator # Added
from .routers import data as data_router # Corrected import
import uvicorn
from .config import settings # Corrected import

app = FastAPI(title="CryptoBot Data Service")

# Instrument the app with Prometheus
Instrumentator().instrument(app).expose(app, include_in_schema=True, should_gzip=True)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_router.router, prefix="/api/v1/data", tags=["data"])

@app.get("/")
async def root():
    return {"message": "CryptoBot Data Service"}

if __name__ == "__main__":
    uvicorn.run(
        "data.main:app", # Fully qualified import string
        host=settings.HOST,
        port=settings.PORT,
        reload=False, # Temporarily disable reloader
        workers=settings.WORKERS
    )