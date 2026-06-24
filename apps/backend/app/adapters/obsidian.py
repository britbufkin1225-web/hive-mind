"""Obsidian vault adapter contract (Phase 6A).

Contract, pure validation, and a non-functional placeholder adapter. This
module does NOT read vault files, scan the filesystem, parse markdown, or watch
files — that is reserved for a future import phase.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from app.adapters.base import SourceAdapter
from app.models.hive_models import (
    ObsidianDocumentCandidate,
    ObsidianLinkStrategy,
    ObsidianVaultConfig,
)

# Allowed link-strategy values, derived from the enum so the two never drift.
LINK_STRATEGIES: frozenset[str] = frozenset(s.value for s in ObsidianLinkStrategy)


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_obsidian_config(data: Mapping[str, Any]) -> list[str]:
    """Validate the *shape* of an Obsidian vault config.

    Pure and filesystem-free: checks field presence and types only. It does
    NOT check whether ``root_path`` exists on the host machine — verifying a
    real location is a future import-phase concern.

    Returns a list of human-readable error strings. An empty list means the
    config shape is valid.
    """
    if not isinstance(data, Mapping):
        return ["config must be a mapping/object"]

    errors: list[str] = []

    vault_id = data.get("vault_id")
    if not isinstance(vault_id, str) or not vault_id.strip():
        errors.append("vault_id is required and must be a non-empty string")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name is required and must be a non-empty string")

    root_path = data.get("root_path")
    if not isinstance(root_path, str) or not root_path.strip():
        errors.append("root_path is required and must be a non-empty string")

    for field in ("include_patterns", "exclude_patterns"):
        value = data.get(field)
        if value is not None and not _is_str_list(value):
            errors.append(f"{field} must be a list of strings if present")

    tag_prefix = data.get("tag_prefix")
    if tag_prefix is not None and not isinstance(tag_prefix, str):
        errors.append("tag_prefix must be a string if present")

    link_strategy = data.get("link_strategy")
    if link_strategy is not None and link_strategy not in LINK_STRATEGIES:
        allowed = ", ".join(sorted(LINK_STRATEGIES))
        errors.append(f"link_strategy must be one of: {allowed}")

    metadata = data.get("metadata")
    if metadata is not None and not isinstance(metadata, Mapping):
        errors.append("metadata must be an object if present")

    return errors


class ObsidianVaultAdapter(SourceAdapter):
    """Placeholder Obsidian adapter (Phase 6A).

    Holds a validated configuration but performs NO vault loading. ``discover()``
    raises NotImplementedError until a future import phase implements real
    traversal and markdown parsing.
    """

    #: Registry source type this adapter corresponds to (see RegistrySourceType).
    source_type = "obsidian"

    def __init__(self, config: ObsidianVaultConfig) -> None:
        self.config = config

    def discover(self) -> Iterable[ObsidianDocumentCandidate]:
        raise NotImplementedError(
            "Obsidian vault import is not implemented in Phase 6A; "
            "this adapter defines the contract only."
        )
