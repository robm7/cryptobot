from fastapi import FastAPI
# Ensure Strategy model is registered with Base metadata for foreign key creation
import strategy.models.strategy # This will execute strategy/models/strategy.py
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator # Added
from .routers import backtest # Corrected import
from .celery_config import celery_app
from database.db import init_db
import asyncio
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start Celery worker (in production this would be separate)
    from celery import current_app
    current_app.conf.task_default_queue = 'backtest'
    logger.info("Celery configured")
    
    yield
    
    # Cleanup
    logger.info("Shutting down")

app = FastAPI(
    title="Backtest Service",
    lifespan=lifespan
)

# Instrument the app with Prometheus
Instrumentator().instrument(app).expose(app, include_in_schema=True, should_gzip=True)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    backtest.router,
    prefix="/api/backtest",
    tags=["backtest"]
)

@app.get("/")
async def root():
    return {"message": "Backtest Service is running"}