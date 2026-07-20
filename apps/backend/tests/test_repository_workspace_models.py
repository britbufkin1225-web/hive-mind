"""Phase 39B - repository workspace contract validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.repository_workspace import (
    MAX_WORKSPACE_DISPLAY_NAME_LENGTH,
    MAX_WORKSPACE_ID_LENGTH,
    MAX_WORKSPACE_RECORDS,
    REPOSITORY_WORKSPACE_SCHEMA_VERSION,
    RepositoryWorkspace,
    RepositoryWorkspaceConfig,
    empty_config,
)


def _workspace(workspace_id: str, root: str, **kwargs) -> RepositoryWorkspace:
    return RepositoryWorkspace(
        workspace_id=workspace_id,
        display_name=kwargs.pop("display_name", f"Workspace {workspace_id}"),
        repository_root=root,
        **kwargs,
    )


def test_valid_empty_configuration() -> None:
    config = empty_config()
    assert config.schema_version == REPOSITORY_WORKSPACE_SCHEMA_VERSION
    assert config.workspaces == []
    assert config.active_workspace_id is None


def test_valid_populated_configuration() -> None:
    config = RepositoryWorkspaceConfig(
        workspaces=[
            _workspace("hive-mind", r"C:\repos\hive-mind"),
            _workspace("zerosoc", r"C:\repos\zerosoc"),
        ],
        active_workspace_id="hive-mind",
    )
    assert len(config.workspaces) == 2
    assert config.get("zerosoc") is not None


def test_unsupported_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig(schema_version="repository-workspaces.v2")


def test_duplicate_workspace_ids_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig(
            workspaces=[
                _workspace("dup", r"C:\repos\a"),
                _workspace("dup", r"C:\repos\b"),
            ]
        )


def test_duplicate_normalized_roots_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig(
            workspaces=[
                _workspace("first", r"C:\repos\Hive-Mind"),
                _workspace("second", "c:/repos/hive-mind/"),
            ]
        )


def test_active_workspace_must_exist() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig(
            workspaces=[_workspace("only", r"C:\repos\only")],
            active_workspace_id="missing",
        )


def test_disabled_active_workspace_is_contract_valid() -> None:
    # "disabled while active" is a resolution-time diagnostic, not a contract
    # violation; the document must still validate.
    config = RepositoryWorkspaceConfig(
        workspaces=[_workspace("only", r"C:\repos\only", enabled=False)],
        active_workspace_id="only",
    )
    assert config.get("only").enabled is False


def test_workspace_id_pattern_enforced() -> None:
    for bad in ("-leading", "has space", "sym$bol", ""):
        with pytest.raises(ValidationError):
            _workspace(bad, r"C:\repos\x")


def test_bounded_field_lengths() -> None:
    with pytest.raises(ValidationError):
        _workspace("x" * (MAX_WORKSPACE_ID_LENGTH + 1), r"C:\repos\x")
    with pytest.raises(ValidationError):
        RepositoryWorkspace(
            workspace_id="ok",
            display_name="d" * (MAX_WORKSPACE_DISPLAY_NAME_LENGTH + 1),
            repository_root=r"C:\repos\x",
        )


def test_oversized_workspace_collection_rejected() -> None:
    workspaces = [
        _workspace(f"ws-{index}", f"C:/repos/repo{index}")
        for index in range(MAX_WORKSPACE_RECORDS + 1)
    ]
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig(workspaces=workspaces)


def test_credential_bearing_remote_rejected() -> None:
    with pytest.raises(ValidationError):
        _workspace(
            "creds",
            r"C:\repos\x",
            expected_remote="https://user:token@github.com/x/y.git",
        )


def test_canonical_remotes_accepted() -> None:
    workspace = _workspace(
        "ok", r"C:\repos\x", expected_remote="git@github.com:x/y.git"
    )
    assert workspace.expected_remote == "git@github.com:x/y.git"


def test_blank_expected_remote_becomes_none() -> None:
    workspace = _workspace("ok", r"C:\repos\x", expected_remote="   ")
    assert workspace.expected_remote is None


def test_normalized_orders_workspaces_by_id() -> None:
    config = RepositoryWorkspaceConfig(
        workspaces=[
            _workspace("zeta", r"C:\repos\z"),
            _workspace("alpha", r"C:\repos\a"),
        ]
    )
    ordered = [item.workspace_id for item in config.normalized().workspaces]
    assert ordered == ["alpha", "zeta"]


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        RepositoryWorkspaceConfig.model_validate(
            {
                "schema_version": REPOSITORY_WORKSPACE_SCHEMA_VERSION,
                "workspaces": [],
                "unexpected": True,
            }
        )
