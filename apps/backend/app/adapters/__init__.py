"""Source adapter contracts for Hive|Mind.

Phase 6A defines the *contract* for future source adapters (starting with
Obsidian): config shapes, a pure validation helper, and a non-functional
adapter placeholder. No adapter in this phase performs filesystem traversal,
markdown parsing, file watching, or vault import.
"""

from app.adapters.base import SourceAdapter
from app.adapters.obsidian import (
    ObsidianVaultAdapter,
    validate_obsidian_config,
)

__all__ = [
    "SourceAdapter",
    "ObsidianVaultAdapter",
    "validate_obsidian_config",
]
