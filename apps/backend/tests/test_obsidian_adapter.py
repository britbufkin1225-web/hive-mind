"""Phase 6A — Obsidian adapter contract tests.

Contract/validation only. These tests must never touch the real filesystem.
"""

import pytest

from app.adapters import ObsidianVaultAdapter, SourceAdapter, validate_obsidian_config
from app.models.hive_models import (
    ObsidianDocumentCandidate,
    ObsidianLinkStrategy,
    ObsidianVaultConfig,
    RegistrySourceType,
    SourceRecordCreate,
)


def valid_config_dict() -> dict:
    return {
        "vault_id": "vault-1",
        "name": "My Vault",
        "root_path": "/vaults/my-vault",
        "include_patterns": ["**/*.md"],
        "exclude_patterns": [".obsidian/**"],
        "tag_prefix": "#",
        "link_strategy": "wikilink",
        "metadata": {"owner": "brit"},
    }


# --------------------------------------------------------------------------- #
# Config shape
# --------------------------------------------------------------------------- #
def test_config_model_defaults() -> None:
    config = ObsidianVaultConfig(
        vault_id="v1", name="Vault", root_path="/some/path"
    )
    assert config.include_patterns == []
    assert config.exclude_patterns == []
    assert config.tag_prefix is None
    assert config.link_strategy is ObsidianLinkStrategy.BOTH
    assert config.metadata == {}


def test_document_candidate_shape() -> None:
    candidate = ObsidianDocumentCandidate(
        source_id="reg-1", source_path="notes/a.md", title="A"
    )
    assert candidate.tags == []
    assert candidate.links == []
    assert candidate.content_preview is None


# --------------------------------------------------------------------------- #
# Pure validation
# --------------------------------------------------------------------------- #
def test_valid_config_passes() -> None:
    assert validate_obsidian_config(valid_config_dict()) == []


def test_missing_required_fields_fail() -> None:
    errors = validate_obsidian_config({"include_patterns": ["**/*.md"]})
    joined = " ".join(errors)
    assert "vault_id" in joined
    assert "name" in joined
    assert "root_path" in joined


def test_blank_name_fails() -> None:
    data = valid_config_dict()
    data["name"] = "   "
    assert any("name" in e for e in validate_obsidian_config(data))


def test_invalid_link_strategy_fails() -> None:
    data = valid_config_dict()
    data["link_strategy"] = "telepathy"
    errors = validate_obsidian_config(data)
    assert any("link_strategy" in e for e in errors)


def test_each_allowed_link_strategy_passes() -> None:
    for strategy in ("wikilink", "markdown", "both"):
        data = valid_config_dict()
        data["link_strategy"] = strategy
        assert validate_obsidian_config(data) == []


def test_non_list_include_exclude_rejected() -> None:
    data = valid_config_dict()
    data["include_patterns"] = "**/*.md"  # string, not a list
    assert any("include_patterns" in e for e in validate_obsidian_config(data))

    data = valid_config_dict()
    data["exclude_patterns"] = [1, 2]  # not a list of strings
    assert any("exclude_patterns" in e for e in validate_obsidian_config(data))


def test_metadata_is_optional() -> None:
    data = valid_config_dict()
    del data["metadata"]
    assert validate_obsidian_config(data) == []


def test_validation_does_not_touch_filesystem() -> None:
    # A path that does not exist on the host must still validate — this phase
    # validates shape only, never host filesystem state.
    data = valid_config_dict()
    data["root_path"] = "/definitely/not/a/real/path/zzz-9f3c"
    assert validate_obsidian_config(data) == []


# --------------------------------------------------------------------------- #
# Source registry compatibility
# --------------------------------------------------------------------------- #
def test_obsidian_is_a_registry_source_type() -> None:
    assert RegistrySourceType.OBSIDIAN.value == "obsidian"
    record = SourceRecordCreate(name="Vault", type="obsidian")
    assert record.type is RegistrySourceType.OBSIDIAN


# --------------------------------------------------------------------------- #
# Adapter placeholder
# --------------------------------------------------------------------------- #
def test_adapter_is_a_source_adapter() -> None:
    config = ObsidianVaultConfig(vault_id="v1", name="V", root_path="/p")
    adapter = ObsidianVaultAdapter(config)
    assert isinstance(adapter, SourceAdapter)
    assert adapter.source_type == "obsidian"
    assert adapter.config is config


def test_adapter_discover_raises_without_filesystem_work() -> None:
    config = ObsidianVaultConfig(vault_id="v1", name="V", root_path="/p")
    adapter = ObsidianVaultAdapter(config)
    with pytest.raises(NotImplementedError):
        list(adapter.discover())
