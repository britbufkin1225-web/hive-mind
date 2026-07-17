"""Phase 37F — Active Memory context-packet API transport schema.

The request contract for the first read-only Active Memory endpoint
(``POST /api/active-memory/context-packet``). This module is a **transport
boundary only**: it mirrors the exact inputs of the Phase 37E builder
(``app.services.active_memory_context_packet.build_context_packet``) and adds no
new context categories, no selection/freshness/contradiction rules, and no
response shape — the response *is* the frozen Phase 37B
:class:`~app.models.active_memory.ContextPacket` contract, reused directly.

Kept in its own module (not added to ``active_memory.py``) because the Phase 37B
contract file is a frozen wire contract mirrored by the frontend; a request
envelope for one backend endpoint is a 37F transport concern, exactly as the 37C
snapshot constants were kept in the store module rather than the contract file.

Design rationale:

* **Caller-supplied clock.** ``generated_at`` is required because the Phase 37E
  builder never observes wall-clock time; the API preserves that determinism
  contract instead of stamping a server time.
* **Records ride in the request.** The 37E builder reads through a
  :class:`~app.store.active_memory_store.MemoryStore`, and no application-level
  Active Memory store instance exists (write endpoints are a later phase). The
  request therefore carries the full record set and the router converts it into
  an ephemeral, request-scoped in-memory store — pure transport conversion, with
  no shared state and no persistence.
* **No competing collection limit.** ``records`` deliberately carries no
  transport-level ``max_length``: the per-collection bounds
  (``MAX_MEMORY_COLLECTION_ITEMS``) are owned by the Phase 37E service, which
  fails closed on overflow. A second cap at the transport edge would mask that
  contract and make the service's overflow behavior unreachable through the API.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.active_memory import (
    MAX_MEMORY_ID_LENGTH,
    MemoryRecord,
    MemoryScope,
)


class ContextPacketRequest(BaseModel):
    """Structured input for one deterministic, read-only context-packet build.

    Field names and nesting follow the Phase 37E builder signature exactly:
    ``project_id``, ``generated_at``, and optional exact ``scope`` map to the
    builder's keyword parameters; ``records`` is the record set the builder reads
    through its store parameter. Nested shapes (:class:`MemoryScope`,
    :class:`MemoryRecord`) are the frozen Phase 37B contract models, so malformed
    nested structures are rejected by the established Pydantic validation path.
    """

    project_id: str = Field(max_length=MAX_MEMORY_ID_LENGTH)
    generated_at: datetime
    scope: MemoryScope | None = None
    records: list[MemoryRecord] = Field(default_factory=list)

    @field_validator("project_id")
    @classmethod
    def _project_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("project_id must not be empty")
        return value.strip()

    @field_validator("records")
    @classmethod
    def _created_at_timezone_awareness_is_consistent(
        cls, value: list[MemoryRecord]
    ) -> list[MemoryRecord]:
        awareness = {
            record.created_at.tzinfo is not None
            and record.created_at.utcoffset() is not None
            for record in value
        }
        if len(awareness) > 1:
            raise ValueError(
                "records created_at timestamps must be consistently "
                "timezone-aware or timezone-naive"
            )
        return value
