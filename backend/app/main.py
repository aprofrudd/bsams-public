"""BSAMS FastAPI Application."""

import logging
import os
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.routers import admin, air_bike, analysis, assessments, athletes, auth, combine, consent, consent_tracking, custom_training_types, database_analysis, events, exercise_library, exercises, data_export, invitations, lactate, metabolic, programme_forms, programs, reports, session_templates, training, training_blocks, uploads, vbt, wellness

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bsams")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="BSAMS API",
    description="Boxing Science Athlete Management System",
    version="1.0.0",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions. Log full traceback, return generic message in production."""
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        str(exc),
        traceback.format_exc(),
    )
    if settings.environment == "development":
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s %d %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    if settings.environment != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://*.supabase.co"
    )
    return response


# CORS configuration — environment-aware
if settings.environment == "development":
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        cors_origins.append(frontend_url)
else:
    frontend_url = os.getenv("FRONTEND_URL")
    cors_origins = [frontend_url] if frontend_url else []

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(athletes.router, prefix=settings.api_v1_prefix)
app.include_router(events.router, prefix=settings.api_v1_prefix)
app.include_router(uploads.router, prefix=settings.api_v1_prefix)
app.include_router(analysis.router, prefix=settings.api_v1_prefix)
app.include_router(training.router, prefix=settings.api_v1_prefix)
app.include_router(custom_training_types.router, prefix=settings.api_v1_prefix)
app.include_router(exercises.router, prefix=settings.api_v1_prefix)
app.include_router(wellness.router, prefix=settings.api_v1_prefix)
app.include_router(exercise_library.router, prefix=settings.api_v1_prefix)
app.include_router(session_templates.router, prefix=settings.api_v1_prefix)
app.include_router(programs.router, prefix=settings.api_v1_prefix)
app.include_router(vbt.router, prefix=settings.api_v1_prefix)
app.include_router(lactate.router, prefix=settings.api_v1_prefix)
app.include_router(air_bike.router, prefix=settings.api_v1_prefix)
app.include_router(metabolic.router, prefix=settings.api_v1_prefix)
app.include_router(assessments.router, prefix=settings.api_v1_prefix)
app.include_router(reports.router, prefix=settings.api_v1_prefix)
app.include_router(invitations.router, prefix=settings.api_v1_prefix)
app.include_router(consent.router, prefix=settings.api_v1_prefix)
app.include_router(consent_tracking.router, prefix=settings.api_v1_prefix)
app.include_router(training_blocks.router, prefix=settings.api_v1_prefix)
app.include_router(programme_forms.router, prefix=settings.api_v1_prefix)
app.include_router(data_export.router, prefix=settings.api_v1_prefix)
app.include_router(database_analysis.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(combine.router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint. Pings database to verify connectivity."""
    client = get_supabase_client()
    if not client:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "Database not configured"},
        )
    try:
        # Lightweight query to verify DB connectivity
        client.table("profiles").select("id").limit(1).execute()
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "Database unreachable"},
        )
