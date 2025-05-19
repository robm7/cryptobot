import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from .routers import trades
from api.routers import settings as api_settings # Import the new settings router
from services.data.logging_middleware import RequestLoggingMiddleware
from database.db import get_db # Assuming get_db is in the common database.db module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Trade Execution Service")

# Instrument the app with Prometheus
Instrumentator().instrument(app).expose(app, include_in_schema=True, should_gzip=True)

# Add logging middleware
app.add_middleware(RequestLoggingMiddleware, logger_name="trade-service", db_session_factory=get_db)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trades.router, prefix="/api/trades")
app.include_router(api_settings.router) # Include the settings router

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=False) # Changed port and added reload=False