"""Source adapter contracts for Hive|Mind.

Phase 6A defines the *contract* for future source adapters (starting with
Obsidian): config shapes, a pure validation helper, and a non-functional
adapter placeholder. No adapter in this phase performs filesystem traversal,
markdown parsing, file watching, or vault import.
"""

from app.adapters.base import SourceAdapter
from app.adapters.markdown_parser import ParsedNote, parse_markdown
from app.adapters.obsidian import (
    ObsidianVaultAdapter,
    validate_obsidian_config,
)
from app.adapters.vault_scanner import (
    resolve_vault_root,
    scan_markdown_files,
)

__all__ = [
    "SourceAdapter",
    "ObsidianVaultAdapter",
    "validate_obsidian_config",
    "ParsedNote",
    "parse_markdown",
    "resolve_vault_root",
    "scan_markdown_files",
]
