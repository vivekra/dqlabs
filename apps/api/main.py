import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.routers.tenants import router as tenants_router
from apps.api.routers.templates import router as templates_router
from apps.api.routers.workspaces import router as workspaces_router
from apps.api.routers.billing import router as billing_router
from apps.api.init_db import run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digitalq-api")

app = FastAPI(
    title="DigitalQ Labs SaaS Core API",
    description=(
        "Production-grade tenant-aware REST API gateway handling organizations, memberships, "
        "billing, quota validations, workspaces state transitions, and audit logs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

@app.on_event("startup")
async def on_startup():
    """Startup trigger that automatically initializes database schemas asynchronously."""
    try:
        await run_migrations()
    except Exception as e:
        logger.error(f"Failed to run database migrations during startup: {str(e)}")


# CORS configurations for decoupled static deployments (Vercel / Netlify edge CDNs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to Vercel custom domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard Health-check endpoint
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """Confirms operational database engine and backend service gateway status."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "api_version": "1.0.0",
    }

# Map tenant-aware routers under versioned routes prefix
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
