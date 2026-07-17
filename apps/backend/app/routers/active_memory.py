"""Phase 37F — read-only Active Memory context-packet endpoint.

The first backend API boundary over the Active Memory layer. The router is
deliberately **thin** (Phase 37F ownership boundary): it validates transport
input, converts it into the Phase 37E service input, invokes the existing
builder, and returns the existing :class:`ContextPacket` contract. Every
deterministic packet rule — record selection, ordering, freshness tie-breaks,
contradiction derivation, warnings, verification summary, collection limits —
stays in ``app.services.active_memory_context_packet`` and its collaborators;
nothing is duplicated or recalculated here.

Operationally read-only: the request carries the complete record set, the store
built from it is ephemeral and request-scoped, and no persistence, filesystem,
clock, or AI/LLM behavior is involved. ``POST`` is used only because the input
is a structured document, not because anything is written.
"""

from fastapi import APIRouter, HTTPException

from app.models.active_memory import ContextPacket
from app.models.active_memory_api import ContextPacketRequest
from app.services.active_memory_context_packet import (
    ContextPacketTruncationUnsupportedError,
    build_context_packet,
)
from app.store.active_memory_store import (
    DuplicateRecordError,
    InMemoryActiveMemoryStore,
)

router = APIRouter(prefix="/api/active-memory")


@router.post("/context-packet", response_model=ContextPacket)
def post_context_packet(payload: ContextPacketRequest) -> ContextPacket:
    """Build a deterministic, read-only pre-action context packet.

    Contract-level failures from the existing service layer are translated to
    422 (matching the ``/api/import`` convention): a duplicate ``record_id`` in
    the supplied records, and the Phase 37E fail-closed collection-overflow
    error. Both carry only the service's own bounded message — no traceback,
    path, or internal object ever reaches the client (unexpected failures fall
    through to the Phase 18B generic 500 handler).
    """
    try:
        store = InMemoryActiveMemoryStore.from_records(payload.records)
    except DuplicateRecordError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        return build_context_packet(
            store=store,
            project_id=payload.project_id,
            generated_at=payload.generated_at,
            scope=payload.scope,
        )
    except ContextPacketTruncationUnsupportedError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
