import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routers.api import router
from app.routers.obsidian import router as obsidian_router
from app.routers.registry import router as registry_router

logger = logging.getLogger("hivemind.api")


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class VaultSummaryResponse(BaseModel):
    totalFiles: int
    totalSources: int
    totalModels: int
    totalNodes: int
    graphMode: str
    message: str


app = FastAPI(title="Hive|Mind API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(registry_router)
app.include_router(obsidian_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a clean, client-safe JSON error for any unhandled exception.

    Phase 18B error-safety guarantee: an unexpected failure must never leak a
    traceback, internal exception text, or a local filesystem path to the
    client. The real error is logged server-side; the response is a generic 500
    using the same ``detail`` shape as handled (HTTPException) errors, so clients
    see one consistent error contract. Expected client errors keep their precise
    status codes — FastAPI's ``HTTPException``/validation handlers run first, so
    this only catches the genuinely unhandled case.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(ok=True, service="hivemind-backend", version="0.1.0")


@app.get("/api/vault/summary", response_model=VaultSummaryResponse)
def get_vault_summary() -> VaultSummaryResponse:
    return VaultSummaryResponse(
        totalFiles=0,
        totalSources=0,
        totalModels=0,
        totalNodes=0,
        graphMode="not_initialized",
        message="Vault foundation ready. Graph logic not implemented in Phase 1.",
    )
