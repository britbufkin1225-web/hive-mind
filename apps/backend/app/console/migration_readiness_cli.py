"""Phase 40K.5 — read-only operator CLI for the migration readiness preflight.

A thin argparse front end over
:class:`app.services.migration_readiness_preflight.MigrationReadinessPreflight`.
It only ever *reads* a readiness manifest JSON file and prints a bounded,
non-secret report; it performs no migration, opens no store, and offers no
execution command (execution is a separately gated Python boundary that requires
an operational authorization object, never a CLI flag).

Exit codes: 0 preflight ``pass``; 10 ``blocked``; 11 ``fail_closed``;
2 manifest access/size error; 3 usage error (including an invalid ``--now``).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

def _ensure_import_path() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


_ensure_import_path()

from app.models.memory_migration_import import SystemUtcClock  # noqa: E402
from app.services.migration_readiness_preflight import (  # noqa: E402
    MigrationReadinessPreflight,
    PreflightOutcome,
)

EXIT_PASS = 0
EXIT_BLOCKED = 10
EXIT_FAIL_CLOSED = 11
EXIT_OPERATION_ERROR = 2
EXIT_USAGE_ERROR = 3

# A readiness manifest is small structured metadata, never a payload.
MAX_MANIFEST_BYTES = 1024 * 1024

_OUTCOME_EXIT = {
    PreflightOutcome.PASS: EXIT_PASS,
    PreflightOutcome.BLOCKED: EXIT_BLOCKED,
    PreflightOutcome.FAIL_CLOSED: EXIT_FAIL_CLOSED,
}


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _load_manifest(path: Path) -> object:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"manifest file not found: {path}")
    size = path.stat().st_size
    if size > MAX_MANIFEST_BYTES:
        raise ValueError(f"manifest exceeds the {MAX_MANIFEST_BYTES}-byte bound")
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_preflight(args: argparse.Namespace) -> int:
    if args.now is not None:
        try:
            parsed = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        except ValueError:
            print("[error] --now must be an ISO-8601 timestamp", file=sys.stderr)
            return EXIT_USAGE_ERROR
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        clock = _FixedClock(parsed)
    else:
        clock = SystemUtcClock()

    try:
        raw = _load_manifest(Path(args.manifest))
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        # A JSON decode error is an unreadable manifest at the CLI boundary; a
        # schema-valid-but-wrong manifest is handled as fail_closed by the service.
        if isinstance(exc, json.JSONDecodeError):
            print("[error] manifest is not valid JSON", file=sys.stderr)
        else:
            print(f"[error] {exc}", file=sys.stderr)
        return EXIT_OPERATION_ERROR

    preflight = MigrationReadinessPreflight(
        clock=clock, max_evidence_age_seconds=args.max_age_seconds
    )
    report = preflight.evaluate_mapping(raw)
    payload = report.model_dump(mode="json")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"outcome: {report.outcome.value}")
        print(f"manifest_identity: {report.manifest_identity}")
        print(f"tool_version: {report.tool_version}")
        if report.active_stop_conditions:
            print("active_stop_conditions:")
            for cond in report.active_stop_conditions:
                print(f"  - {cond}")
        if report.blocked_reasons:
            print("blocked_reasons:")
            for reason in report.blocked_reasons:
                print(f"  - {reason.value}")
        print("checks:")
        for check in report.checks:
            reason = f" ({check.blocked_reason.value})" if check.blocked_reason else ""
            print(f"  - {check.check_id.value}: {check.state.value}{reason}")

    return _OUTCOME_EXIT[report.outcome]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migration_readiness_cli",
        description=(
            "Read-only production migration readiness preflight. Never mutates "
            "state and never authorizes execution."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight", help="evaluate a readiness manifest read-only")
    p.add_argument("--manifest", required=True, help="path to a readiness manifest JSON")
    p.add_argument("--json", action="store_true", help="emit the machine-readable report")
    p.add_argument(
        "--now",
        default=None,
        help="ISO-8601 trusted evaluation time (deterministic); default system UTC",
    )
    p.add_argument(
        "--max-age-seconds",
        type=int,
        default=24 * 60 * 60,
        help="max age of declared trusted evidence before it is treated as stale",
    )
    p.set_defaults(func=_cmd_preflight, command="preflight")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
