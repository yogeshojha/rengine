from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.config import settings
from app.core.database import init_db
from app.core.logging import logger
from app.utils.helpers import create_initial_admin


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # app starts up
    logger.info("Starting Backend...")
    try:
        await init_db()
        await create_initial_admin()
    except Exception as e:
        logger.exception("Failed to initialize the application: %s", e)
        raise e
    yield
    logger.info("Shutting down reNgine Backend...")
    # app shuts down, cleanup later if reuqired


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    logger.debug("Root endpoint accessed")
    return {
        "message": "Welcome to reNgine API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
