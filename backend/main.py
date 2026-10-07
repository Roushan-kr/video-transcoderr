import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.base import Base
from db.models import User, Video  # Ensure models are registered with Base metadata
from db.db import engine
from routes import auth, videos, internal

logger = logging.getLogger("uvicorn.info")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create all tables on startup if database is reachable
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}. Tables will need to be created once DB is available.")
    yield


app = FastAPI(
    title="Cloud Video Transcoder API",
    description="Production-ready Adaptive Bitrate (ABR) Video Transcoding Service",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(videos.router, prefix="/videos", tags=["Videos"])
app.include_router(internal.router, prefix="/internal", tags=["Internal Transcoder Webhook"])


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "video-transcoder-backend",
        "version": "1.0.0",
    }