from fastapi import FastAPI

from apps.api.app.api.v1.health import router as health_router
from apps.api.app.api.v1.legal import router as legal_router

app = FastAPI(
    title="LegalLens AI - Legal Engine",
    version="0.1.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)
app.include_router(legal_router)


@app.get("/")
def index() -> dict[str, str]:
    return {
        "message": "LegalLens AI FastAPI engine activo",
        "docs": "/docs",
        "health": "/health",
    }

