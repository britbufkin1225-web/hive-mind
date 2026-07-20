"""Phase 39B - path and remote normalization + config-path resolution tests."""

from __future__ import annotations

import unicodedata

import pytest

from app.services.repository_workspace_config import (
    WORKSPACE_CONFIG_ENV,
    WorkspaceConfigPathError,
    resolve_workspace_config_path,
)
from app.services.workspace_paths import (
    display_repository_root,
    normalize_remote,
    remote_has_credentials,
    repository_root_comparison_key,
)


# --------------------------------------------------------------------------- #
# Comparison key
# --------------------------------------------------------------------------- #
def test_trailing_separator_is_ignored() -> None:
    assert repository_root_comparison_key(r"C:\Repo\\") == repository_root_comparison_key(
        r"C:\Repo"
    )


def test_slash_direction_is_normalized() -> None:
    assert repository_root_comparison_key(r"C:\Repo\sub") == repository_root_comparison_key(
        "C:/Repo/sub"
    )


def test_windows_case_insensitive_paths_match() -> None:
    assert repository_root_comparison_key(r"C:\Users\Brit\Repo") == (
        repository_root_comparison_key("c:/users/brit/repo")
    )


def test_duplicate_slashes_collapse() -> None:
    assert repository_root_comparison_key("C:/Repo//sub///deep") == (
        repository_root_comparison_key("C:/Repo/sub/deep")
    )


def test_unicode_paths_compare_by_nfc() -> None:
    nfc = unicodedata.normalize("NFC", "C:/café/repo")
    nfd = unicodedata.normalize("NFD", "C:/café/repo")
    assert nfc != nfd
    assert repository_root_comparison_key(nfc) == repository_root_comparison_key(nfd)


def test_spaces_in_paths_are_preserved_in_key() -> None:
    key = repository_root_comparison_key(r"C:\My Repos\hive mind")
    assert "my repos/hive mind" in key


def test_display_preserves_operator_readable_form() -> None:
    assert display_repository_root("  C:/My Repos/hive-mind  ") == "C:/My Repos/hive-mind"


# --------------------------------------------------------------------------- #
# Remote helpers
# --------------------------------------------------------------------------- #
def test_https_and_ssh_remotes_normalize_equally() -> None:
    https = normalize_remote("https://github.com/britbufkin1225-web/hive-mind.git")
    ssh = normalize_remote("git@github.com:britbufkin1225-web/hive-mind.git")
    assert https == ssh == "github.com/britbufkin1225-web/hive-mind"


def test_credential_bearing_remotes_are_detected() -> None:
    assert remote_has_credentials("https://user:token@github.com/x/y.git")
    assert remote_has_credentials("https://ghp_secrettoken@github.com/x/y.git")


def test_canonical_ssh_remotes_are_not_credentials() -> None:
    assert not remote_has_credentials("git@github.com:x/y.git")
    assert not remote_has_credentials("ssh://git@github.com/x/y.git")
    assert not remote_has_credentials("https://github.com/x/y.git")


# --------------------------------------------------------------------------- #
# Config-path resolution
# --------------------------------------------------------------------------- #
def test_explicit_environment_override_wins() -> None:
    env = {WORKSPACE_CONFIG_ENV: r"D:\custom\workspaces.json", "LOCALAPPDATA": r"C:\A"}
    resolved = resolve_workspace_config_path(env, system="nt")
    assert str(resolved) == r"D:\custom\workspaces.json"


def test_blank_override_is_rejected() -> None:
    with pytest.raises(WorkspaceConfigPathError):
        resolve_workspace_config_path({WORKSPACE_CONFIG_ENV: "   "}, system="nt")


def test_windows_local_appdata_resolution() -> None:
    env = {"LOCALAPPDATA": r"C:\Users\brit\AppData\Local"}
    resolved = resolve_workspace_config_path(env, system="nt")
    assert resolved.name == "repository-workspaces.json"
    from pathlib import PureWindowsPath
    parts = PureWindowsPath(resolved).parts
    assert "HiveMind" in parts
    assert "AppData" in parts


def test_windows_home_fallback_when_no_local_appdata() -> None:
    env = {"USERPROFILE": r"C:\Users\brit"}
    resolved = resolve_workspace_config_path(env, system="nt")
    from pathlib import PureWindowsPath
    parts = PureWindowsPath(resolved).parts
    assert "AppData" in parts and "Local" in parts and "HiveMind" in parts


def test_posix_xdg_resolution() -> None:
    env = {"XDG_CONFIG_HOME": "/home/brit/.config"}
    resolved = resolve_workspace_config_path(env, system="posix")
    assert resolved.as_posix() == "/home/brit/.config/hive-mind/repository-workspaces.json"


def test_posix_home_fallback() -> None:
    env = {"HOME": "/home/brit"}
    resolved = resolve_workspace_config_path(env, system="posix")
    assert resolved.as_posix() == "/home/brit/.config/hive-mind/repository-workspaces.json"


def test_override_preserves_spaces_and_unicode() -> None:
    target = r"C:\My Repos\café\workspaces.json"
    resolved = resolve_workspace_config_path({WORKSPACE_CONFIG_ENV: target}, system="nt")
    assert str(resolved) == target


def test_resolution_does_not_create_anything(tmp_path) -> None:
    target = tmp_path / "does-not-exist" / "workspaces.json"
    resolved = resolve_workspace_config_path(
        {WORKSPACE_CONFIG_ENV: str(target)}, system="nt"
    )
    assert resolved == target
    assert not target.parent.exists()
    assert not target.exists()
