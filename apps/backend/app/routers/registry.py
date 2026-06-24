"""Phase 5A — Source Registry API.

Additive resource at /api/registry/sources for registering future import
connectors. Separate from the graph's /api/sources (HiveSource) resource.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.hive_models import (
    SourceRecord,
    SourceRecordCreate,
    SourceRecordUpdate,
    SourceRegistryListResponse,
)
from app.store.registry import registry

router = APIRouter(prefix="/api/registry")


@router.get("/sources", response_model=SourceRegistryListResponse)
def list_sources() -> SourceRegistryListResponse:
    return SourceRegistryListResponse(sources=registry.list_sources())


@router.post("/sources", response_model=SourceRecord, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceRecordCreate) -> SourceRecord:
    return registry.create_source(payload)


@router.get("/sources/{source_id}", response_model=SourceRecord)
def get_source(source_id: str) -> SourceRecord:
    record = registry.get_source(source_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return record


@router.patch("/sources/{source_id}", response_model=SourceRecord)
def update_source(source_id: str, payload: SourceRecordUpdate) -> SourceRecord:
    record = registry.update_source(source_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return record
