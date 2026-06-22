from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class StatusResponse(BaseModel):
    app: str
    parent: str
    environment: str
    backend: str
    frontend: str


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


@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(ok=True, service="hivemind-backend", version="0.1.0")


@app.get("/api/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return StatusResponse(
        app="Hive|Mind",
        parent="devdevbuilds",
        environment="development",
        backend="online",
        frontend="connected",
    )


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

