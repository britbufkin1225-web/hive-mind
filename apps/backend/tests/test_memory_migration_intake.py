"""Phase 40E — memory-migration intake-safety assessment tests.

Focused coverage of the deterministic, read-only intake boundary: custody and
provenance acceptance, declared path and entry-kind safety, format and container
support, declared digests and bounds, cross-artifact identity, declared-total
reconciliation, derived status, and the determinism and value-safety properties
the diagnostics promise.

Two fixture styles, used deliberately, following the Phase 40D convention:

* **canonical typed fixtures** for everything a legitimate declaration can build;
* **``model_copy`` tampering** for the cases the ``memory-migration.v1`` contract
  makes unreachable through normal construction. Those cases are part of the
  reason this boundary restates contract rules: a declaration that reaches the
  assessor by any path other than full model construction must still be caught.

Every test drives the pure core from explicit fixtures — no store, no clock, no
Git, no filesystem, no archive, no network — so a passing run proves determinism
rather than assuming it.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.models.active_memory import MemorySource, MemorySourceType
from app.models.memory_migration import (
    MAX_MIGRATION_BUNDLE_ARTIFACTS,
    MEMORY_MIGRATION_CONTRACT_VERSION,
    DeclaredArtifactDigest,
    MemoryMigrationBundle,
    MigrationArtifactDescriptor,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
    MigrationEntryKind,
    MigrationIntakeStatus,
    MigrationProvenance,
)
from app.models.memory_migration_assessment import (
    MAX_MIGRATION_DIAGNOSTICS,
    MIGRATION_DIAGNOSTIC_SEVERITY,
    MigrationDiagnosticCode,
    MigrationDiagnosticSeverity,
)
from app.services import memory_migration_intake as intake_module
from app.services.memory_migration_intake import (
    ACCEPTED_CUSTODY_KINDS,
    ACCEPTED_DIGEST_ALGORITHMS,
    ACCEPTED_SOURCE_TYPES,
    MAX_DECLARED_ARTIFACT_BYTES,
    MAX_DECLARED_ARTIFACTS,
    MAX_DECLARED_BUNDLE_BYTES,
    MEMORY_MIGRATION_INTAKE_POLICY_VERSION,
    PARSEABLE_ARTIFACT_FORMATS,
    SAFE_ENTRY_KINDS,
    SUPPORTED_CONTAINER_KINDS,
    UNSAFE_ENTRY_KINDS,
    MemoryMigrationIntakeAssessor,
    MemoryMigrationIntakeLimits,
    assess_memory_migration_intake,
)

SHA256_VALUE = "a" * 64
EXPORTED_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
ACQUIRED_AT = datetime(2026, 6, 2, 9, 0, 0, tzinfo=timezone.utc)
NAIVE_INSTANT = datetime(2026, 6, 1, 12, 0, 0)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _artifact(**overrides: Any) -> MigrationArtifactDescriptor:
    fields: dict[str, Any] = {
        "artifact_id": "artifact-conversations",
        "declared_relative_path": "conversations.json",
        "entry_kind": MigrationEntryKind.FILE,
        "artifact_format": MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        "container": MigrationContainerKind.SINGLE_FILE,
        "declared_byte_size": 4096,
        "declared_digest": DeclaredArtifactDigest(
            algorithm=MigrationDigestAlgorithm.SHA256, value=SHA256_VALUE
        ),
    }
    fields.update(overrides)
    return MigrationArtifactDescriptor(**fields)


def _provenance(**overrides: Any) -> MigrationProvenance:
    fields: dict[str, Any] = {
        "custody": MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
        "source": MemorySource(
            source_type=MemorySourceType.CHATGPT, source_id="chatgpt-export"
        ),
    }
    fields.update(overrides)
    return MigrationProvenance(**fields)


def _bundle(**overrides: Any) -> MemoryMigrationBundle:
    fields: dict[str, Any] = {
        "bundle_id": "bundle-user-history",
        "provenance": _provenance(),
        "artifacts": [_artifact()],
    }
    fields.update(overrides)
    return MemoryMigrationBundle(**fields)


def _codes(bundle: MemoryMigrationBundle, **kwargs: Any) -> set[MigrationDiagnosticCode]:
    report = assess_memory_migration_intake(bundle, **kwargs)
    return {diagnostic.code for diagnostic in report.diagnostics}


# --------------------------------------------------------------------------- #
# The ready path
# --------------------------------------------------------------------------- #
def test_a_well_formed_declaration_reaches_ready_for_parsing() -> None:
    report = assess_memory_migration_intake(_bundle())

    assert report.assessed_status is MigrationIntakeStatus.READY_FOR_PARSING
    assert report.ready_for_parsing is True
    assert report.declared_status is MigrationIntakeStatus.DECLARED
    assert report.artifact_count == 1
    assert report.read_only is True
    assert report.artifacts_read is False


def test_ready_still_carries_the_standing_unverified_digest_notice() -> None:
    # Readiness is not an integrity claim. The advisory is emitted for every
    # clean declaration precisely so a reader cannot mistake "a digest is
    # present" for "the digest checked out".
    report = assess_memory_migration_intake(_bundle())

    assert [item.code for item in report.diagnostics] == [
        MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED
    ]
    assert report.advisory_diagnostics == report.diagnostics
    assert report.ready_for_parsing is True


def test_the_unverified_notice_is_bundle_scoped_and_counted() -> None:
    artifacts = [
        _artifact(artifact_id=f"artifact-{index}", declared_relative_path=f"{index}.json")
        for index in range(4)
    ]
    report = assess_memory_migration_intake(_bundle(artifacts=artifacts))

    (notice,) = report.advisory_diagnostics
    assert notice.artifact_id is None
    assert "4 declared digest(s)" in notice.message


def test_the_report_binds_its_verdict_to_the_exact_declaration() -> None:
    bundle = _bundle()
    report = assess_memory_migration_intake(bundle)

    assert report.bundle_fingerprint == bundle.fingerprint()
    assert report.permits_parsing(bundle_fingerprint=bundle.fingerprint()) is True

    edited = _bundle(artifacts=[_artifact(declared_byte_size=8192)])
    assert report.permits_parsing(bundle_fingerprint=edited.fingerprint()) is False


# --------------------------------------------------------------------------- #
# Custody and provenance
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("custody", sorted(ACCEPTED_CUSTODY_KINDS))
def test_user_controlled_custody_is_accepted(custody: MigrationCustodyKind) -> None:
    provenance = _provenance(
        custody=custody,
        declared_exported_at=EXPORTED_AT,
    )
    assert MigrationDiagnosticCode.REFUSED_CUSTODY not in _codes(
        _bundle(provenance=provenance)
    )


@pytest.mark.parametrize(
    "custody",
    [
        MigrationCustodyKind.THIRD_PARTY_TRANSFER,
        MigrationCustodyKind.AUTOMATED_ACCOUNT_LINK,
    ],
)
def test_non_user_custody_quarantines(custody: MigrationCustodyKind) -> None:
    # Hive|Mind claims no direct, account-to-account access to a provider's
    # private system memory. Material described as arriving that way is refused
    # at the boundary rather than accepted with a caveat.
    report = assess_memory_migration_intake(_bundle(provenance=_provenance(custody=custody)))

    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    assert report.ready_for_parsing is False
    assert MigrationDiagnosticCode.REFUSED_CUSTODY in {
        item.code for item in report.quarantine_diagnostics
    }


@pytest.mark.parametrize("source_type", sorted(ACCEPTED_SOURCE_TYPES))
def test_user_attributable_source_types_are_accepted(
    source_type: MemorySourceType,
) -> None:
    provenance = _provenance(
        source=MemorySource(source_type=source_type, source_id="origin")
    )
    assert MigrationDiagnosticCode.UNSUPPORTED_SOURCE_TYPE not in _codes(
        _bundle(provenance=provenance)
    )


@pytest.mark.parametrize(
    "source_type",
    [
        MemorySourceType.REPOSITORY_OBSERVER,
        MemorySourceType.CI_SYSTEM,
        MemorySourceType.CLI_REPORT,
        MemorySourceType.UNKNOWN,
    ],
)
def test_internal_and_unattributable_source_types_block(
    source_type: MemorySourceType,
) -> None:
    # A user bundle declaring a Hive|Mind internal producer as its origin would
    # launder that producer's authority onto unread bytes.
    provenance = _provenance(
        source=MemorySource(source_type=source_type, source_id="origin")
    )
    report = assess_memory_migration_intake(_bundle(provenance=provenance))

    assert report.assessed_status is MigrationIntakeStatus.BLOCKED
    assert MigrationDiagnosticCode.UNSUPPORTED_SOURCE_TYPE in {
        item.code for item in report.diagnostics
    }


def test_a_requested_export_must_declare_when_it_was_produced() -> None:
    provenance = _provenance(custody=MigrationCustodyKind.USER_REQUESTED_EXPORT)
    assert MigrationDiagnosticCode.MISSING_DECLARED_EXPORT_TIME in _codes(
        _bundle(provenance=provenance)
    )

    dated = _provenance(
        custody=MigrationCustodyKind.USER_REQUESTED_EXPORT,
        declared_exported_at=EXPORTED_AT,
    )
    assert MigrationDiagnosticCode.MISSING_DECLARED_EXPORT_TIME not in _codes(
        _bundle(provenance=dated)
    )


def test_an_impossible_custody_timeline_blocks() -> None:
    provenance = _provenance(
        declared_exported_at=ACQUIRED_AT, declared_acquired_at=EXPORTED_AT
    )
    assert MigrationDiagnosticCode.INCONSISTENT_CUSTODY_TIMELINE in _codes(
        _bundle(provenance=provenance)
    )


def test_incomparable_timestamps_are_skipped_rather_than_normalized() -> None:
    # Assuming a timezone for a naive declaration would be exactly the silent
    # normalization this phase forbids, so the timeline check is skipped and the
    # declared values are left intact.
    provenance = _provenance(
        declared_exported_at=EXPORTED_AT, declared_acquired_at=NAIVE_INSTANT
    )
    assert MigrationDiagnosticCode.INCONSISTENT_CUSTODY_TIMELINE not in _codes(
        _bundle(provenance=provenance)
    )


# --------------------------------------------------------------------------- #
# Declared path safety
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("../conversations.json", MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH),
        ("a/../../b.json", MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH),
        ("..\\escape.json", MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH),
        ("/etc/passwd", MigrationDiagnosticCode.ABSOLUTE_ARTIFACT_PATH),
        ("C:/Users/x/export.zip", MigrationDiagnosticCode.ABSOLUTE_ARTIFACT_PATH),
        ("chat\x00.json", MigrationDiagnosticCode.CONTROL_CHARACTER_IN_PATH),
        ("chat\x1b[0m.json", MigrationDiagnosticCode.CONTROL_CHARACTER_IN_PATH),
        ("NUL", MigrationDiagnosticCode.RESERVED_DEVICE_PATH_SEGMENT),
        ("export/COM1.json", MigrationDiagnosticCode.RESERVED_DEVICE_PATH_SEGMENT),
    ],
)
def test_structurally_unsafe_paths_quarantine(
    path: str, code: MigrationDiagnosticCode
) -> None:
    report = assess_memory_migration_intake(
        _bundle(artifacts=[_artifact(declared_relative_path=path)])
    )

    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    assert code in {item.code for item in report.quarantine_diagnostics}


@pytest.mark.parametrize(
    "path",
    [
        " leading.json",
        "trailing.json ",
        "nested//double.json",
        "./relative.json",
        "trailing/",
        "windows\\separator.json",
        "spaced /segment.json",
    ],
)
def test_non_canonical_paths_block_and_are_never_rewritten(path: str) -> None:
    bundle = _bundle(artifacts=[_artifact(declared_relative_path=path)])
    report = assess_memory_migration_intake(bundle)

    assert report.assessed_status is MigrationIntakeStatus.BLOCKED
    assert MigrationDiagnosticCode.NON_CANONICAL_ARTIFACT_PATH in {
        item.code for item in report.diagnostics
    }
    # The declaration is reported, never repaired: the path is identity-bearing.
    assert bundle.artifacts[0].declared_relative_path == path


@pytest.mark.parametrize(
    "path",
    [
        "conversations.json",
        "export/conversations.json",
        "deeply/nested/dir/chat-2026-06-01.md",
        "unicode-café.md",
        "console.json",
        "nul-prefixed.json",
    ],
)
def test_ordinary_relative_paths_raise_no_path_finding(path: str) -> None:
    path_codes = {
        MigrationDiagnosticCode.ABSOLUTE_ARTIFACT_PATH,
        MigrationDiagnosticCode.TRAVERSING_ARTIFACT_PATH,
        MigrationDiagnosticCode.CONTROL_CHARACTER_IN_PATH,
        MigrationDiagnosticCode.RESERVED_DEVICE_PATH_SEGMENT,
        MigrationDiagnosticCode.NON_CANONICAL_ARTIFACT_PATH,
    }
    found = _codes(_bundle(artifacts=[_artifact(declared_relative_path=path)]))
    assert not (found & path_codes)


# --------------------------------------------------------------------------- #
# Declared entry kinds
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", sorted(UNSAFE_ENTRY_KINDS))
def test_link_and_device_entries_quarantine(kind: MigrationEntryKind) -> None:
    report = assess_memory_migration_intake(
        _bundle(artifacts=[_artifact(entry_kind=kind)])
    )

    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    assert MigrationDiagnosticCode.UNSAFE_ENTRY_KIND in {
        item.code for item in report.quarantine_diagnostics
    }


@pytest.mark.parametrize(
    "kind", [MigrationEntryKind.DIRECTORY, MigrationEntryKind.UNKNOWN]
)
def test_undeclarable_entry_kinds_block_rather_than_quarantine(
    kind: MigrationEntryKind,
) -> None:
    # Recoverable by declaring the actual files, so the declaration is at fault
    # rather than the material.
    report = assess_memory_migration_intake(
        _bundle(artifacts=[_artifact(entry_kind=kind)])
    )

    assert report.assessed_status is MigrationIntakeStatus.BLOCKED
    assert MigrationDiagnosticCode.UNSUPPORTED_ENTRY_KIND in {
        item.code for item in report.diagnostics
    }


def test_entry_kind_policy_partitions_the_whole_vocabulary() -> None:
    # Every member is explicitly safe, explicitly unsafe, or falls through to the
    # blocking branch — there is no member the assessor silently ignores.
    assert not (SAFE_ENTRY_KINDS & UNSAFE_ENTRY_KINDS)
    assert SAFE_ENTRY_KINDS == frozenset({MigrationEntryKind.FILE})


# --------------------------------------------------------------------------- #
# Formats and containers
# --------------------------------------------------------------------------- #
def test_unrecognized_format_blocks_with_its_own_code() -> None:
    assert MigrationDiagnosticCode.UNRECOGNIZED_ARTIFACT_FORMAT in _codes(
        _bundle(
            artifacts=[
                _artifact(artifact_format=MigrationArtifactFormat.UNRECOGNIZED)
            ]
        )
    )


def test_recognized_but_unparseable_format_blocks_distinctly() -> None:
    # Recognition is not support: the diagnostic must say "no parser for this",
    # not the uninformative "unknown".
    found = _codes(
        _bundle(
            artifacts=[
                _artifact(
                    artifact_format=MigrationArtifactFormat.OBSIDIAN_VAULT_EXPORT
                )
            ]
        )
    )
    assert MigrationDiagnosticCode.UNSUPPORTED_ARTIFACT_FORMAT in found
    assert MigrationDiagnosticCode.UNRECOGNIZED_ARTIFACT_FORMAT not in found


def test_directory_tree_container_blocks_because_its_entries_are_unstated() -> None:
    found = _codes(
        _bundle(
            artifacts=[
                _artifact(
                    artifact_format=MigrationArtifactFormat.CURATED_MARKDOWN_BUNDLE,
                    container=MigrationContainerKind.DIRECTORY_TREE,
                )
            ]
        )
    )
    assert MigrationDiagnosticCode.UNSUPPORTED_CONTAINER_KIND in found
    # An unsupported container short-circuits the format/container consistency
    # check: there is no meaningful pairing to assess.
    assert MigrationDiagnosticCode.FORMAT_CONTAINER_MISMATCH not in found


@pytest.mark.parametrize(
    ("artifact_format", "container"),
    [
        (
            MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE,
            MigrationContainerKind.SINGLE_FILE,
        ),
        (
            MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
            MigrationContainerKind.ZIP_ARCHIVE,
        ),
        (
            MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT,
            MigrationContainerKind.ZIP_ARCHIVE,
        ),
    ],
)
def test_contradictory_format_and_container_blocks(
    artifact_format: MigrationArtifactFormat, container: MigrationContainerKind
) -> None:
    assert MigrationDiagnosticCode.FORMAT_CONTAINER_MISMATCH in _codes(
        _bundle(
            artifacts=[
                _artifact(artifact_format=artifact_format, container=container)
            ]
        )
    )


@pytest.mark.parametrize(
    ("artifact_format", "container"),
    [
        (
            MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE,
            MigrationContainerKind.ZIP_ARCHIVE,
        ),
        (
            MigrationArtifactFormat.CURATED_MARKDOWN_BUNDLE,
            MigrationContainerKind.ZIP_ARCHIVE,
        ),
        (
            MigrationArtifactFormat.CURATED_JSON_BUNDLE,
            MigrationContainerKind.SINGLE_FILE,
        ),
    ],
)
def test_consistent_format_and_container_pairings_are_accepted(
    artifact_format: MigrationArtifactFormat, container: MigrationContainerKind
) -> None:
    report = assess_memory_migration_intake(
        _bundle(
            artifacts=[
                _artifact(artifact_format=artifact_format, container=container)
            ]
        )
    )
    assert report.ready_for_parsing is True


# --------------------------------------------------------------------------- #
# Declared digests
# --------------------------------------------------------------------------- #
def test_a_missing_digest_blocks_because_no_later_phase_could_verify_it() -> None:
    assert MigrationDiagnosticCode.MISSING_DECLARED_DIGEST in _codes(
        _bundle(artifacts=[_artifact(declared_digest=None)])
    )


@pytest.mark.parametrize(
    ("algorithm", "value"),
    [
        (MigrationDigestAlgorithm.MD5, "b" * 32),
        (MigrationDigestAlgorithm.SHA1, "c" * 40),
    ],
)
def test_weak_digest_algorithms_block(
    algorithm: MigrationDigestAlgorithm, value: str
) -> None:
    found = _codes(
        _bundle(
            artifacts=[
                _artifact(
                    declared_digest=DeclaredArtifactDigest(
                        algorithm=algorithm, value=value
                    )
                )
            ]
        )
    )
    assert MigrationDiagnosticCode.WEAK_DIGEST_ALGORITHM in found
    # A blocked digest is not also described as "declared but unverified": that
    # would imply it could become verified later, and it cannot.
    assert MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED not in found


@pytest.mark.parametrize("algorithm", sorted(ACCEPTED_DIGEST_ALGORITHMS))
def test_accepted_digest_algorithms_reach_ready(
    algorithm: MigrationDigestAlgorithm,
) -> None:
    from app.models.memory_migration import DIGEST_HEX_LENGTHS

    digest = DeclaredArtifactDigest(
        algorithm=algorithm, value="d" * DIGEST_HEX_LENGTHS[algorithm]
    )
    report = assess_memory_migration_intake(
        _bundle(artifacts=[_artifact(declared_digest=digest)])
    )
    assert report.ready_for_parsing is True


# --------------------------------------------------------------------------- #
# Declared bounds and totals
# --------------------------------------------------------------------------- #
def test_the_initial_policy_bounds_are_the_declared_values() -> None:
    assert MAX_DECLARED_ARTIFACT_BYTES == 1 * 1024 * 1024 * 1024
    assert MAX_DECLARED_BUNDLE_BYTES == 2 * 1024 * 1024 * 1024
    assert MAX_DECLARED_ARTIFACTS == 512
    assert MEMORY_MIGRATION_INTAKE_POLICY_VERSION == "memory-migration-intake.v1"


def test_a_missing_declared_size_blocks() -> None:
    assert MigrationDiagnosticCode.MISSING_DECLARED_SIZE in _codes(
        _bundle(artifacts=[_artifact(declared_byte_size=None)])
    )


def test_an_oversized_artifact_blocks_and_is_never_clipped() -> None:
    oversized = MAX_DECLARED_ARTIFACT_BYTES + 1
    bundle = _bundle(artifacts=[_artifact(declared_byte_size=oversized)])
    report = assess_memory_migration_intake(bundle)

    assert MigrationDiagnosticCode.ARTIFACT_SIZE_LIMIT_EXCEEDED in {
        item.code for item in report.diagnostics
    }
    assert bundle.artifacts[0].declared_byte_size == oversized


def test_an_oversized_bundle_total_blocks() -> None:
    limits = MemoryMigrationIntakeLimits(
        max_artifact_bytes=1_000, max_bundle_bytes=1_500
    )
    artifacts = [
        _artifact(
            artifact_id=f"artifact-{index}",
            declared_relative_path=f"{index}.json",
            declared_byte_size=900,
        )
        for index in range(2)
    ]
    found = _codes(_bundle(artifacts=artifacts), limits=limits)
    assert MigrationDiagnosticCode.BUNDLE_SIZE_LIMIT_EXCEEDED in found


def test_an_understated_bundle_total_cannot_slip_under_the_ceiling() -> None:
    # The larger of the two declared views is bounded, so neither an understated
    # bundle total nor understated artifact sizes buys headroom.
    limits = MemoryMigrationIntakeLimits(
        max_artifact_bytes=1_000, max_bundle_bytes=1_000
    )
    bundle = _bundle(
        artifacts=[
            _artifact(
                artifact_id=f"artifact-{index}",
                declared_relative_path=f"{index}.json",
                declared_byte_size=800,
            )
            for index in range(2)
        ],
        declared_total_byte_size=10,
    )
    found = _codes(bundle, limits=limits)
    assert MigrationDiagnosticCode.BUNDLE_SIZE_LIMIT_EXCEEDED in found
    assert MigrationDiagnosticCode.DECLARED_SIZE_MISMATCH in found


def test_too_many_declared_artifacts_blocks() -> None:
    limits = MemoryMigrationIntakeLimits(max_artifacts=2)
    artifacts = [
        _artifact(artifact_id=f"artifact-{index}", declared_relative_path=f"{index}.json")
        for index in range(3)
    ]
    assert MigrationDiagnosticCode.ARTIFACT_COUNT_LIMIT_EXCEEDED in _codes(
        _bundle(artifacts=artifacts), limits=limits
    )


def test_declared_totals_are_recomputed_and_reconciled() -> None:
    found = _codes(_bundle(declared_artifact_count=7, declared_total_byte_size=99))
    assert MigrationDiagnosticCode.DECLARED_COUNT_MISMATCH in found
    assert MigrationDiagnosticCode.DECLARED_SIZE_MISMATCH in found


def test_accurate_declared_totals_raise_no_finding() -> None:
    report = assess_memory_migration_intake(
        _bundle(declared_artifact_count=1, declared_total_byte_size=4096)
    )
    assert report.ready_for_parsing is True


def test_a_partial_size_declaration_reports_only_the_missing_size() -> None:
    # Comparing a partial sum against a declared total would produce a second,
    # misleading mismatch finding on top of the real one.
    found = _codes(
        _bundle(
            artifacts=[
                _artifact(),
                _artifact(
                    artifact_id="artifact-second",
                    declared_relative_path="second.json",
                    declared_byte_size=None,
                ),
            ],
            declared_total_byte_size=4096,
        )
    )
    assert MigrationDiagnosticCode.MISSING_DECLARED_SIZE in found
    assert MigrationDiagnosticCode.DECLARED_SIZE_MISMATCH not in found


def test_an_empty_bundle_blocks() -> None:
    report = assess_memory_migration_intake(_bundle(artifacts=[]))

    assert report.assessed_status is MigrationIntakeStatus.BLOCKED
    assert MigrationDiagnosticCode.EMPTY_BUNDLE in {
        item.code for item in report.diagnostics
    }


# --------------------------------------------------------------------------- #
# Cross-artifact declared identity
# --------------------------------------------------------------------------- #
def test_two_artifacts_at_one_path_block() -> None:
    artifacts = [
        _artifact(artifact_id="artifact-a", declared_byte_size=1),
        _artifact(artifact_id="artifact-b", declared_byte_size=2),
    ]
    found = _codes(_bundle(artifacts=artifacts))
    assert MigrationDiagnosticCode.DUPLICATE_ARTIFACT_PATH in found
    assert MigrationDiagnosticCode.REDUNDANT_ARTIFACT_DECLARATION not in found


def test_the_same_material_declared_twice_blocks_as_redundant() -> None:
    artifacts = [_artifact(artifact_id="artifact-a"), _artifact(artifact_id="artifact-b")]
    found = _codes(_bundle(artifacts=artifacts))
    assert MigrationDiagnosticCode.REDUNDANT_ARTIFACT_DECLARATION in found


def test_paths_differing_only_in_case_are_not_treated_as_one() -> None:
    # Case folding here would invent an equivalence this phase cannot verify:
    # the two are genuinely different on a case-sensitive filesystem.
    artifacts = [
        _artifact(artifact_id="artifact-a", declared_relative_path="Chat.json"),
        _artifact(artifact_id="artifact-b", declared_relative_path="chat.json"),
    ]
    assert MigrationDiagnosticCode.DUPLICATE_ARTIFACT_PATH not in _codes(
        _bundle(artifacts=artifacts)
    )


# --------------------------------------------------------------------------- #
# Restated contract rules (tampered declarations)
# --------------------------------------------------------------------------- #
def test_a_tampered_schema_version_is_caught_at_the_boundary() -> None:
    tampered = _bundle().model_copy(update={"schema_version": "memory-migration.v9"})
    found = _codes(tampered)
    assert MigrationDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION in found


def test_a_tampered_artifact_schema_version_is_caught_per_artifact() -> None:
    artifact = _artifact().model_copy(update={"schema_version": "memory-migration.v9"})
    report = assess_memory_migration_intake(_bundle(artifacts=[artifact]))

    version_findings = [
        item
        for item in report.diagnostics
        if item.code is MigrationDiagnosticCode.UNSUPPORTED_CONTRACT_VERSION
    ]
    assert [item.artifact_id for item in version_findings] == [artifact.artifact_id]


def test_a_bundle_asserting_its_own_readiness_is_refused() -> None:
    tampered = _bundle().model_copy(
        update={"intake_status": MigrationIntakeStatus.READY_FOR_PARSING}
    )
    report = assess_memory_migration_intake(tampered)

    assert report.declared_status is MigrationIntakeStatus.READY_FOR_PARSING
    assert report.assessed_status is MigrationIntakeStatus.BLOCKED
    assert report.ready_for_parsing is False
    assert MigrationDiagnosticCode.UNSUPPORTED_INTAKE_STATUS in {
        item.code for item in report.diagnostics
    }


# --------------------------------------------------------------------------- #
# Escalation, bounds on the report, and determinism
# --------------------------------------------------------------------------- #
def test_quarantine_dominates_blocking_findings() -> None:
    artifacts = [
        _artifact(artifact_id="artifact-a", declared_digest=None),
        _artifact(
            artifact_id="artifact-b",
            declared_relative_path="../escape.json",
        ),
    ]
    report = assess_memory_migration_intake(_bundle(artifacts=artifacts))

    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    assert report.blocking_diagnostics
    assert report.quarantine_diagnostics


def _overflowing_bundle(*, include_unsafe: bool) -> MemoryMigrationBundle:
    artifacts = [
        _artifact(
            artifact_id=f"artifact-{index:04d}",
            declared_relative_path=f"chat-{index:04d}.json",
            declared_byte_size=None,
            declared_digest=None,
        )
        for index in range(300)
    ]
    if include_unsafe:
        artifacts.append(
            _artifact(
                artifact_id="artifact-unsafe",
                declared_relative_path="link.json",
                entry_kind=MigrationEntryKind.SYMLINK,
            )
        )
    return _bundle(artifacts=artifacts)


def test_overflowing_findings_are_bounded_and_the_truncation_is_declared() -> None:
    report = assess_memory_migration_intake(_overflowing_bundle(include_unsafe=False))

    assert len(report.diagnostics) == MAX_MIGRATION_DIAGNOSTICS
    assert MigrationDiagnosticCode.DIAGNOSTICS_TRUNCATED in {
        item.code for item in report.diagnostics
    }
    assert report.ready_for_parsing is False


def test_truncation_cannot_soften_the_derived_status() -> None:
    # Retention is most-severe-first, so the single quarantine finding among 600
    # blocking ones survives and the verdict stays quarantined.
    report = assess_memory_migration_intake(_overflowing_bundle(include_unsafe=True))

    assert len(report.diagnostics) == MAX_MIGRATION_DIAGNOSTICS
    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    assert MigrationDiagnosticCode.UNSAFE_ENTRY_KIND in {
        item.code for item in report.quarantine_diagnostics
    }


def test_diagnostics_are_canonically_ordered_and_unique() -> None:
    artifacts = [
        _artifact(
            artifact_id="artifact-b",
            declared_relative_path="../b.json",
            declared_digest=None,
        ),
        _artifact(
            artifact_id="artifact-a",
            declared_relative_path=" a.json",
            declared_byte_size=None,
        ),
    ]
    report = assess_memory_migration_intake(_bundle(artifacts=artifacts))

    keys = [item.sort_key() for item in report.diagnostics]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))
    assert len(keys) > 1


def test_the_same_declaration_always_yields_the_same_report() -> None:
    first = assess_memory_migration_intake(_bundle())
    second = assess_memory_migration_intake(_bundle())
    assert first.model_dump() == second.model_dump()


def test_the_assessor_is_stateless_between_calls() -> None:
    assessor = MemoryMigrationIntakeAssessor()
    clean = _bundle()
    unsafe = _bundle(artifacts=[_artifact(entry_kind=MigrationEntryKind.SYMLINK)])

    first = assessor.assess(clean)
    assessor.assess(unsafe)
    third = assessor.assess(clean)

    assert first.model_dump() == third.model_dump()


def test_artifact_declaration_order_does_not_change_the_verdict() -> None:
    first = _artifact(artifact_id="artifact-a", declared_relative_path="a.json")
    second = _artifact(artifact_id="artifact-b", declared_relative_path="../b.json")

    forward = assess_memory_migration_intake(_bundle(artifacts=[first, second]))
    reverse = assess_memory_migration_intake(_bundle(artifacts=[second, first]))

    assert forward.model_dump() == reverse.model_dump()


def test_the_assessor_never_mutates_the_declaration_it_reads() -> None:
    bundle = _bundle(
        artifacts=[
            _artifact(
                declared_relative_path="../ escape.json",
                declared_byte_size=MAX_DECLARED_ARTIFACT_BYTES + 1,
            )
        ]
    )
    before = bundle.model_dump()
    assess_memory_migration_intake(bundle)
    assert bundle.model_dump() == before


# --------------------------------------------------------------------------- #
# Policy limits
# --------------------------------------------------------------------------- #
def test_the_assessor_defaults_to_the_declared_intake_policy() -> None:
    assessor = MemoryMigrationIntakeAssessor()
    assert assessor.limits == MemoryMigrationIntakeLimits()
    assert assessor.policy_version == MEMORY_MIGRATION_INTAKE_POLICY_VERSION


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"max_artifacts": 0}, "positive integer"),
        ({"max_artifact_bytes": -1}, "positive integer"),
        ({"max_bundle_bytes": True}, "positive integer"),
        (
            {"max_artifacts": MAX_MIGRATION_BUNDLE_ARTIFACTS + 1},
            "contract ceiling",
        ),
        (
            {"max_artifact_bytes": 10, "max_bundle_bytes": 5},
            "must not exceed max_bundle_bytes",
        ),
    ],
)
def test_intake_limits_reject_incoherent_policy(
    kwargs: dict[str, Any], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        MemoryMigrationIntakeLimits(**kwargs)


def test_policy_allowlists_stay_within_the_contract_vocabulary() -> None:
    assert PARSEABLE_ARTIFACT_FORMATS < frozenset(MigrationArtifactFormat)
    assert SUPPORTED_CONTAINER_KINDS < frozenset(MigrationContainerKind)
    assert ACCEPTED_CUSTODY_KINDS < frozenset(MigrationCustodyKind)
    assert ACCEPTED_DIGEST_ALGORITHMS < frozenset(MigrationDigestAlgorithm)
    assert ACCEPTED_SOURCE_TYPES < frozenset(MemorySourceType)
    assert MigrationArtifactFormat.UNRECOGNIZED not in PARSEABLE_ARTIFACT_FORMATS


# --------------------------------------------------------------------------- #
# Every code is reachable, and no declared value is ever echoed
# --------------------------------------------------------------------------- #
def _all_reachable_codes() -> set[MigrationDiagnosticCode]:
    scenarios: list[MemoryMigrationBundle] = [
        _bundle(),
        _bundle(artifacts=[]),
        _bundle(artifacts=[_artifact(declared_digest=None, declared_byte_size=None)]),
        _bundle(artifacts=[_artifact(declared_relative_path="../escape.json")]),
        _bundle(artifacts=[_artifact(declared_relative_path="/abs.json")]),
        _bundle(artifacts=[_artifact(declared_relative_path="chat\x00.json")]),
        _bundle(artifacts=[_artifact(declared_relative_path="CON.json")]),
        _bundle(artifacts=[_artifact(declared_relative_path=" spaced.json")]),
        _bundle(artifacts=[_artifact(entry_kind=MigrationEntryKind.SYMLINK)]),
        _bundle(artifacts=[_artifact(entry_kind=MigrationEntryKind.DIRECTORY)]),
        _bundle(
            artifacts=[
                _artifact(artifact_format=MigrationArtifactFormat.UNRECOGNIZED)
            ]
        ),
        _bundle(
            artifacts=[
                _artifact(
                    artifact_format=MigrationArtifactFormat.OBSIDIAN_VAULT_EXPORT
                )
            ]
        ),
        _bundle(
            artifacts=[
                _artifact(container=MigrationContainerKind.DIRECTORY_TREE)
            ]
        ),
        _bundle(artifacts=[_artifact(container=MigrationContainerKind.ZIP_ARCHIVE)]),
        _bundle(
            artifacts=[
                _artifact(
                    declared_digest=DeclaredArtifactDigest(
                        algorithm=MigrationDigestAlgorithm.MD5, value="b" * 32
                    )
                )
            ]
        ),
        _bundle(artifacts=[_artifact(declared_byte_size=MAX_DECLARED_ARTIFACT_BYTES + 1)]),
        _bundle(declared_artifact_count=9, declared_total_byte_size=9),
        _bundle(
            artifacts=[
                _artifact(artifact_id="artifact-a"),
                _artifact(artifact_id="artifact-b"),
            ]
        ),
        _bundle(
            artifacts=[
                _artifact(artifact_id="artifact-a", declared_byte_size=1),
                _artifact(artifact_id="artifact-b", declared_byte_size=2),
            ]
        ),
        _bundle(
            provenance=_provenance(
                custody=MigrationCustodyKind.AUTOMATED_ACCOUNT_LINK
            )
        ),
        _bundle(
            provenance=_provenance(
                source=MemorySource(
                    source_type=MemorySourceType.UNKNOWN, source_id="x"
                )
            )
        ),
        _bundle(
            provenance=_provenance(custody=MigrationCustodyKind.USER_REQUESTED_EXPORT)
        ),
        _bundle(
            provenance=_provenance(
                declared_exported_at=ACQUIRED_AT, declared_acquired_at=EXPORTED_AT
            )
        ),
        _bundle().model_copy(update={"schema_version": "memory-migration.v9"}),
        _bundle().model_copy(
            update={"intake_status": MigrationIntakeStatus.QUARANTINED}
        ),
        _overflowing_bundle(include_unsafe=False),
    ]
    found: set[MigrationDiagnosticCode] = set()
    for bundle in scenarios:
        found |= _codes(bundle)
    # Two bundle-total codes need a narrowed policy to be reachable at realistic
    # declared sizes.
    narrow = MemoryMigrationIntakeLimits(max_artifact_bytes=1, max_bundle_bytes=1)
    found |= _codes(_bundle(), limits=narrow)
    found |= _codes(
        _bundle(
            artifacts=[
                _artifact(artifact_id=f"artifact-{i}", declared_relative_path=f"{i}.json")
                for i in range(3)
            ]
        ),
        limits=MemoryMigrationIntakeLimits(max_artifacts=1),
    )
    return found


def test_every_diagnostic_code_is_reachable_from_a_real_declaration() -> None:
    # A taxonomy member no declaration can produce is a rule nobody enforces.
    assert _all_reachable_codes() == set(MigrationDiagnosticCode)


def test_no_diagnostic_message_echoes_a_declared_value() -> None:
    # The values this phase inspects are the ones most likely to be hostile or
    # sensitive; echoing one would move the problem into the record of the
    # declaration.
    secrets = [
        "../../etc/passwd",
        "svc-user:s3cr3t-token@example.invalid",
        "personal-therapy-notes.json",
        "e" * 64,
        "application/x-secret-type",
        "My ChatGPT Account Export",
    ]
    bundle = _bundle(
        label=secrets[5],
        provenance=_provenance(declared_origin_label=secrets[5]),
        artifacts=[
            _artifact(
                artifact_id="artifact-probe",
                declared_relative_path=secrets[0],
                declared_media_type=secrets[4],
                label=secrets[2],
                declared_digest=DeclaredArtifactDigest(
                    algorithm=MigrationDigestAlgorithm.SHA256, value=secrets[3]
                ),
                metadata={"origin_note": secrets[1]},
            )
        ],
    )
    report = assess_memory_migration_intake(bundle)

    assert report.assessed_status is MigrationIntakeStatus.QUARANTINED
    for diagnostic in report.diagnostics:
        for secret in secrets:
            assert secret not in diagnostic.message


def test_diagnostic_severities_match_the_taxonomy_at_runtime() -> None:
    report = assess_memory_migration_intake(
        _bundle(artifacts=[_artifact(entry_kind=MigrationEntryKind.SYMLINK)])
    )
    for diagnostic in report.diagnostics:
        assert diagnostic.severity is MIGRATION_DIAGNOSTIC_SEVERITY[diagnostic.code]
        assert diagnostic.blocks_parsing is (
            diagnostic.severity is not MigrationDiagnosticSeverity.ADVISORY
        )


# --------------------------------------------------------------------------- #
# Purity
# --------------------------------------------------------------------------- #
_FORBIDDEN_CALLS = {
    "now",
    "utcnow",
    "today",
    "monotonic",
    "time",
    "uuid1",
    "uuid4",
    "random",
    "shuffle",
    "choice",
    "getenv",
    "open",
    "read_text",
    "read_bytes",
    "run",
    "urlopen",
    "system",
    "popen",
    "extractall",
    "namelist",
    "listdir",
    "walk",
    "resolve",
    "exists",
    "stat",
}
_FORBIDDEN_IMPORTS = {
    "os",
    "random",
    "secrets",
    "shutil",
    "socket",
    "subprocess",
    "tarfile",
    "time",
    "urllib",
    "uuid",
    "zipfile",
    "requests",
    "httpx",
    "pathlib",
}


def test_intake_module_opens_nothing_and_reads_no_clock_or_filesystem() -> None:
    # The boundary that decides whether untrusted material may be touched must
    # itself not touch it. This is enforced structurally, not by convention.
    tree = ast.parse(Path(inspect.getfile(intake_module)).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in _FORBIDDEN_IMPORTS, alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in _FORBIDDEN_IMPORTS, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in _FORBIDDEN_CALLS, name


def test_the_contract_version_the_boundary_implements_is_pinned() -> None:
    assert MEMORY_MIGRATION_CONTRACT_VERSION == "memory-migration.v1"
