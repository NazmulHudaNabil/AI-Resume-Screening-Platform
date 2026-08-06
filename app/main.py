from fastapi import FastAPI
from app.core.config import settings
from app.api.router import api_router

from contextlib import asynccontextmanager
import logging
import os
from pythonjsonlogger import jsonlogger
import redis.asyncio as redis
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id

# Configure structured JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Remove default handlers
for handler in logger.handlers:
    logger.removeHandler(handler)

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s')
logHandler.setFormatter(formatter)

# Also write logs to a file
os.makedirs("logs", exist_ok=True)
fileHandler = logging.FileHandler("logs/app.log")
fileHandler.setFormatter(formatter)

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id.get()
        return True

logger.addFilter(CorrelationIdFilter())
logger.addHandler(logHandler)
logger.addHandler(fileHandler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup any lifespan items (e.g. redis connections for other parts of the app)
    # The custom rate limiter uses its own client or can be tied here.
    yield

app = FastAPI(
    title=settings.app_name,
    description="A platform to screen resumes using AI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

@app.get("/")
async def home():
    return {"message":"AI Resume Screening Platfrom"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify that the API is up and running.
    """
    return {"status": "ok", "app_name": settings.app_name}

# Include all API routes
app.include_router(api_router)
