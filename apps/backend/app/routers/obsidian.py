"""Phase 6B — Obsidian import API.

A single one-shot import endpoint at ``POST /api/obsidian/import``. It scans an
explicit local vault path and imports markdown notes into the graph store. The
import is read-only over the vault; it never modifies the user's files.
"""

from fastapi import APIRouter, HTTPException

from app.models.hive_models import ObsidianImportRequest, ObsidianImportSummary
from app.services.obsidian_import import import_vault

router = APIRouter(prefix="/api/obsidian")


@router.post("/import", response_model=ObsidianImportSummary)
def post_import(payload: ObsidianImportRequest) -> ObsidianImportSummary:
    """Import markdown notes from an explicit Obsidian vault path.

    A bad vault path (empty, missing, or not a directory) is a client error and
    returns HTTP 400. Per-file read/parse failures do not fail the request —
    they are reported in the summary's ``error_count``/``warnings``.
    """
    try:
        return import_vault(payload.vault_path, payload.source_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
