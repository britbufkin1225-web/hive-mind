"""Phase 39B - operator CLI for the persistent repository workspace registry.

This is the authoritative command surface behind the PowerShell operator tool. It
is a thin argparse front end over
``app.services.repository_workspace_config``; all validation, path resolution,
atomic persistence, and diagnostics live in the service so the two front ends
never diverge.

Commands: ``path``, ``init``, ``list``, ``show``, ``add``, ``set-active``,
``remove``, ``validate``. Every command supports ``--json`` for machine-readable
output. Exit codes: 0 success, 2 operation/configuration error, 3 usage/invalid
invocation (including an invalid environment override).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_import_path() -> None:
    # Allow running this file directly (python <path>/repository_workspace_cli.py)
    # by making the backend package root importable.
    backend_root = Path(__file__).resolve().parents[2]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


_ensure_import_path()

from app.services.repository_workspace_config import (  # noqa: E402
    CredentialBearingRemoteError,
    DuplicateRepositoryRootError,
    DuplicateWorkspaceError,
    RepositoryWorkspaceConfigService,
    UnsupportedWorkspaceSchemaVersionError,
    WorkspaceConfigExistsError,
    WorkspaceConfigInaccessibleError,
    WorkspaceConfigMalformedError,
    WorkspaceConfigNotFoundError,
    WorkspaceConfigPathError,
    WorkspaceConfigSaveError,
    WorkspaceConfigTooLargeError,
    WorkspaceFieldError,
    WorkspaceNotFoundError,
    WorkspaceOperationError,
)

EXIT_OK = 0
EXIT_OPERATION_ERROR = 2
EXIT_USAGE_ERROR = 3


def _service(args: argparse.Namespace) -> RepositoryWorkspaceConfigService:
    config_path = Path(args.config_path) if args.config_path else None
    return RepositoryWorkspaceConfigService(config_path=config_path)


def _workspace_dict(workspace) -> dict:
    return {
        "workspace_id": workspace.workspace_id,
        "display_name": workspace.display_name,
        "repository_root": workspace.repository_root,
        "expected_remote": workspace.expected_remote,
        "enabled": workspace.enabled,
    }


def _emit(args: argparse.Namespace, payload: dict, human_lines: list[str]) -> None:
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for line in human_lines:
            print(line)


def _fail(args: argparse.Namespace, error: str, message: str, exit_code: int) -> int:
    payload = {
        "command": getattr(args, "command", None),
        "status": "error",
        "error": error,
        "message": message,
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"[error] {getattr(args, 'command', '?')}: {message}", file=sys.stderr)
    return exit_code


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
def _cmd_path(args: argparse.Namespace) -> int:
    service = _service(args)
    exists = service.exists()
    payload = {
        "command": "path",
        "status": "ok",
        "config_path": str(service.path),
        "exists": exists,
    }
    _emit(
        args,
        payload,
        [f"config_path: {service.path}", f"exists: {str(exists).lower()}"],
    )
    return EXIT_OK


def _cmd_init(args: argparse.Namespace) -> int:
    service = _service(args)
    service.initialize(overwrite=args.overwrite)
    payload = {
        "command": "init",
        "status": "ok",
        "config_path": str(service.path),
        "overwrite": args.overwrite,
    }
    _emit(args, payload, [f"initialized empty configuration at {service.path}"])
    return EXIT_OK


def _cmd_list(args: argparse.Namespace) -> int:
    service = _service(args)
    config = service.load_or_default().normalized()
    payload = {
        "command": "list",
        "status": "ok",
        "config_path": str(service.path),
        "active_workspace_id": config.active_workspace_id,
        "workspaces": [_workspace_dict(item) for item in config.workspaces],
    }
    lines = [f"config_path: {service.path}"]
    lines.append(f"active_workspace_id: {config.active_workspace_id or '(none)'}")
    if not config.workspaces:
        lines.append("(no workspaces registered)")
    for item in config.workspaces:
        marker = "*" if item.workspace_id == config.active_workspace_id else " "
        state = "enabled" if item.enabled else "disabled"
        lines.append(
            f" {marker} {item.workspace_id}  [{state}]  {item.display_name}  "
            f"-> {item.repository_root}"
        )
    _emit(args, payload, lines)
    return EXIT_OK


def _cmd_show(args: argparse.Namespace) -> int:
    service = _service(args)
    config = service.load_or_default()
    workspace = config.get(args.id)
    if workspace is None:
        return _fail(
            args,
            "WorkspaceNotFoundError",
            f"workspace {args.id!r} does not exist",
            EXIT_OPERATION_ERROR,
        )
    payload = {
        "command": "show",
        "status": "ok",
        "config_path": str(service.path),
        "active": config.active_workspace_id == workspace.workspace_id,
        "workspace": _workspace_dict(workspace),
    }
    lines = [
        f"workspace_id: {workspace.workspace_id}",
        f"display_name: {workspace.display_name}",
        f"repository_root: {workspace.repository_root}",
        f"expected_remote: {workspace.expected_remote or '(none)'}",
        f"enabled: {str(workspace.enabled).lower()}",
        f"active: {str(config.active_workspace_id == workspace.workspace_id).lower()}",
    ]
    _emit(args, payload, lines)
    return EXIT_OK


def _cmd_add(args: argparse.Namespace) -> int:
    service = _service(args)
    workspace = service.add_workspace(
        workspace_id=args.id,
        display_name=args.name,
        repository_root=args.repository_root,
        expected_remote=args.expected_remote,
        enabled=not args.disabled,
        make_active=args.activate,
    )
    payload = {
        "command": "add",
        "status": "ok",
        "config_path": str(service.path),
        "activated": args.activate,
        "workspace": _workspace_dict(workspace),
    }
    _emit(args, payload, [f"added workspace {workspace.workspace_id}"])
    return EXIT_OK


def _cmd_set_active(args: argparse.Namespace) -> int:
    service = _service(args)
    workspace = service.set_active_workspace(args.id)
    payload = {
        "command": "set-active",
        "status": "ok",
        "config_path": str(service.path),
        "active_workspace_id": workspace.workspace_id,
    }
    _emit(args, payload, [f"active workspace set to {workspace.workspace_id}"])
    return EXIT_OK


def _cmd_remove(args: argparse.Namespace) -> int:
    service = _service(args)
    workspace = service.remove_workspace(args.id)
    payload = {
        "command": "remove",
        "status": "ok",
        "config_path": str(service.path),
        "removed_workspace_id": workspace.workspace_id,
    }
    _emit(args, payload, [f"removed workspace {workspace.workspace_id}"])
    return EXIT_OK


def _cmd_validate(args: argparse.Namespace) -> int:
    service = _service(args)
    report = service.validate()
    payload = {"command": "validate", "status": "ok", **report.model_dump(mode="json")}
    lines = [
        f"config_path: {report.config_path}",
        f"schema_version: {report.schema_version}",
        f"active_workspace_id: {report.active_workspace_id or '(none)'}",
        f"workspace_count: {report.workspace_count}",
        f"active_resolved: {str(report.active_resolution.resolved).lower()}",
    ]
    for availability in report.workspaces:
        codes = ", ".join(d.code for d in availability.diagnostics) or "ok"
        lines.append(f" - {availability.workspace_id}: {codes}")
    _emit(args, payload, lines)
    return EXIT_OK


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repository_workspace_cli",
        description="Manage the local Hive|Mind repository workspace registry.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--config-path",
        default=None,
        help="explicit configuration file path (overrides env resolution)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_path = sub.add_parser("path", help="show the resolved configuration path")
    p_path.set_defaults(func=_cmd_path, command="path")

    p_init = sub.add_parser("init", help="initialize an empty configuration")
    p_init.add_argument("--overwrite", action="store_true", help="replace an existing file")
    p_init.set_defaults(func=_cmd_init, command="init")

    p_list = sub.add_parser("list", help="list registered workspaces")
    p_list.set_defaults(func=_cmd_list, command="list")

    p_show = sub.add_parser("show", help="show one workspace")
    p_show.add_argument("--id", required=True, help="workspace identifier")
    p_show.set_defaults(func=_cmd_show, command="show")

    p_add = sub.add_parser("add", help="register a repository workspace")
    p_add.add_argument("--id", required=True, help="stable workspace identifier")
    p_add.add_argument("--name", required=True, help="human-readable display name")
    p_add.add_argument(
        "--repository-root", required=True, help="absolute repository root path"
    )
    p_add.add_argument(
        "--expected-remote", default=None, help="optional expected canonical remote"
    )
    p_add.add_argument("--disabled", action="store_true", help="register as disabled")
    p_add.add_argument(
        "--activate", action="store_true", help="also select as the active workspace"
    )
    p_add.set_defaults(func=_cmd_add, command="add")

    p_active = sub.add_parser("set-active", help="select the active workspace")
    p_active.add_argument("--id", required=True, help="workspace identifier")
    p_active.set_defaults(func=_cmd_set_active, command="set-active")

    p_remove = sub.add_parser("remove", help="remove a workspace")
    p_remove.add_argument("--id", required=True, help="workspace identifier")
    p_remove.set_defaults(func=_cmd_remove, command="remove")

    p_validate = sub.add_parser(
        "validate", help="validate configuration and repository availability"
    )
    p_validate.set_defaults(func=_cmd_validate, command="validate")

    return parser


_USAGE_ERRORS = (WorkspaceConfigPathError,)
_OPERATION_ERRORS = (
    WorkspaceConfigNotFoundError,
    WorkspaceConfigMalformedError,
    UnsupportedWorkspaceSchemaVersionError,
    WorkspaceConfigInaccessibleError,
    WorkspaceConfigTooLargeError,
    WorkspaceConfigExistsError,
    WorkspaceConfigSaveError,
    DuplicateWorkspaceError,
    DuplicateRepositoryRootError,
    WorkspaceNotFoundError,
    CredentialBearingRemoteError,
    WorkspaceFieldError,
    WorkspaceOperationError,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except _USAGE_ERRORS as exc:
        return _fail(args, type(exc).__name__, str(exc), EXIT_USAGE_ERROR)
    except _OPERATION_ERRORS as exc:
        return _fail(args, type(exc).__name__, str(exc), EXIT_OPERATION_ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
