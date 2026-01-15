from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

# Load env vars
load_dotenv()

from src.routes import auth, holidays, leaves, users, policies
from src.services.scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Leave Management System", lifespan=lifespan)

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
app.include_router(auth.router)
app.include_router(holidays.router)
app.include_router(holidays.calendar_router)
app.include_router(leaves.router)
app.include_router(users.router)
app.include_router(policies.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Leave Management System API is running"}
