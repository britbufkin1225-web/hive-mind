"""Phase 6B — safe, read-only Obsidian vault scanner.

Walks a vault directory and yields markdown files only, deterministically. It
never follows symlinks, never descends into hidden/system folders, and never
escapes the selected vault root. It performs no writes of any kind.
"""

from __future__ import annotations

import os
from pathlib import Path

#: System/tooling folders that are never part of importable vault content.
#: Hidden directories (names starting with ``.``) are excluded separately, so
#: ``.obsidian`` and ``.git`` are covered by that rule too; they are listed here
#: for documentation and defence in depth.
IGNORED_DIRS: frozenset[str] = frozenset({".obsidian", ".git", "node_modules"})

MARKDOWN_SUFFIX = ".md"


def _is_ignored_dir(name: str) -> bool:
    return name.startswith(".") or name in IGNORED_DIRS


def resolve_vault_root(vault_path: str) -> Path:
    """Validate and resolve a vault path.

    Raises ``ValueError`` if the path is empty, malformed, does not exist, or is
    not a directory. Returns the resolved absolute path on success.

    Phase 18B hardening: a malformed path *string* (embedded null byte, invalid
    OS path syntax, or a name that exceeds the OS limit) can make the filesystem
    probe itself raise ``OSError``/``ValueError``. The import path is the highest-
    risk untrusted input, so those are normalized into a single ``ValueError``
    here — the router maps it to a clean HTTP 400 instead of leaking an unhandled
    500. The probe is read-only; nothing is created or modified.
    """
    if not vault_path or not vault_path.strip():
        raise ValueError("vault_path must not be empty")
    try:
        path = Path(vault_path).expanduser()
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
    except (OSError, ValueError) as exc:
        raise ValueError(f"vault_path is not a valid path: {vault_path}") from exc
    if not exists:
        raise ValueError(f"vault_path does not exist: {vault_path}")
    if not is_dir:
        raise ValueError(f"vault_path is not a directory: {vault_path}")
    return path.resolve()


def scan_markdown_files(root: Path) -> list[Path]:
    """Return absolute paths of ``.md`` files under ``root``, sorted.

    Skips hidden/system directories and hidden files, ignores non-markdown
    files, does not follow symlinked directories or files, and never returns a
    path outside ``root``.
    """
    root = root.resolve()
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune in place so os.walk never descends into ignored/hidden dirs.
        dirnames[:] = sorted(d for d in dirnames if not _is_ignored_dir(d))
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            if not name.lower().endswith(MARKDOWN_SUFFIX):
                continue
            full = Path(dirpath) / name
            if full.is_symlink():
                continue
            try:
                full.resolve().relative_to(root)
            except ValueError:
                continue  # defensive: never escape the vault root
            results.append(full)
    return results


def relative_vault_path(full_path: Path, root: Path) -> str:
    """Return ``full_path`` relative to ``root`` as a POSIX string (stable)."""
    return full_path.resolve().relative_to(root.resolve()).as_posix()
