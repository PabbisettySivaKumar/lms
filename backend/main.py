import time
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()

from backend.routes import auth, holidays, leaves, users, policies
from backend.services.scheduler import start_scheduler, shutdown_scheduler
from backend.db import init_db, close_db
from backend.utils.logging_config import setup_logging

# Configure logging (file + console) on import
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()  # Initialize SQLAlchemy and create tables
    start_scheduler()
    logger.info("Application started")
    yield
    # Shutdown
    shutdown_scheduler()
    await close_db()  # Close database connections
    logger.info("Application shutdown")


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Leave Management System", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request: method, path, status, duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
@app.get("/")
async def root():
    return {"message": "Leave Management System API is running"}

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(leaves.router)
app.include_router(holidays.router)
app.include_router(holidays.calendar_router)
app.include_router(policies.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


