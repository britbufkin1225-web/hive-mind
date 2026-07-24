"""Phase 40E — ``memory-migration.v1`` contract tests.

Focused coverage of the declaration and assessment-result contracts: version
pinning, the pinned safety flags that carry this phase's load-bearing claims,
bounded metadata, digest representability, identity-bearing path handling,
deterministic fingerprint derivation, and the lifecycle vocabulary's deliberate
gaps.

The tests that assert an *absence* — no ``parsed``/``approved``/``persisted``
lifecycle member, no way to set ``is_memory``, no way to declare
``ready_for_parsing`` — are the load-bearing ones. Phase 40E's value is what it
refuses to be able to express, and an absence is only guaranteed if something
fails when it reappears.

Every test constructs contracts from explicit literals — no store, no clock, no
Git, no filesystem, no network — so a passing run proves determinism rather than
assuming it.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.models.active_memory import (
    LifecycleState,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models import memory_migration as mm_module
from app.models.memory_migration import (
    CANDIDATE_MEMORY_POLICY,
    DIGEST_HEX_LENGTHS,
    MAX_MIGRATION_METADATA_ENTRIES,
    MEMORY_MIGRATION_CONTRACT_VERSION,
    CandidateMemoryPolicy,
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
    derive_artifact_fingerprint,
    derive_bundle_fingerprint,
    derive_migration_id,
)
from app.models.memory_migration_assessment import (
    MEMORY_MIGRATION_ASSESSMENT_VERSION,
    MIGRATION_DIAGNOSTIC_SEVERITY,
    MemoryMigrationIntakeAssessment,
    MigrationDiagnosticCode,
    MigrationDiagnosticSeverity,
    MigrationIntakeDiagnostic,
    resolve_intake_status,
)

SHA256_VALUE = "a" * 64
SHA512_VALUE = "b" * 128
EXPORTED_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
ACQUIRED_AT = datetime(2026, 6, 2, 9, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _digest(
    algorithm: MigrationDigestAlgorithm = MigrationDigestAlgorithm.SHA256,
    value: str = SHA256_VALUE,
) -> DeclaredArtifactDigest:
    return DeclaredArtifactDigest(algorithm=algorithm, value=value)


def _artifact(**overrides: Any) -> MigrationArtifactDescriptor:
    fields: dict[str, Any] = {
        "artifact_id": "artifact-conversations",
        "declared_relative_path": "conversations.json",
        "entry_kind": MigrationEntryKind.FILE,
        "artifact_format": MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON,
        "container": MigrationContainerKind.SINGLE_FILE,
        "declared_byte_size": 4096,
        "declared_digest": _digest(),
    }
    fields.update(overrides)
    return MigrationArtifactDescriptor(**fields)


def _provenance(**overrides: Any) -> MigrationProvenance:
    fields: dict[str, Any] = {
        "custody": MigrationCustodyKind.USER_REQUESTED_EXPORT,
        "source": MemorySource(
            source_type=MemorySourceType.CHATGPT,
            source_id="chatgpt-export:2026-06-01",
        ),
        "declared_exported_at": EXPORTED_AT,
        "declared_acquired_at": ACQUIRED_AT,
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


# --------------------------------------------------------------------------- #
# Contract version
# --------------------------------------------------------------------------- #
def test_contract_version_is_the_declared_literal() -> None:
    assert MEMORY_MIGRATION_CONTRACT_VERSION == "memory-migration.v1"
    assert MEMORY_MIGRATION_ASSESSMENT_VERSION == "memory-migration-assessment.v1"


@pytest.mark.parametrize(
    "builder",
    [_provenance, _artifact, _bundle, CandidateMemoryPolicy],
    ids=["provenance", "artifact", "bundle", "candidate_policy"],
)
def test_every_record_defaults_to_and_pins_the_contract_version(builder: Any) -> None:
    assert builder().schema_version == MEMORY_MIGRATION_CONTRACT_VERSION
    with pytest.raises(ValidationError, match="unsupported schema_version"):
        builder(schema_version="memory-migration.v2")


def _digest_with(**overrides: Any) -> DeclaredArtifactDigest:
    fields: dict[str, Any] = {
        "algorithm": MigrationDigestAlgorithm.SHA256,
        "value": SHA256_VALUE,
    }
    fields.update(overrides)
    return DeclaredArtifactDigest(**fields)


@pytest.mark.parametrize(
    "builder",
    [_provenance, _artifact, _bundle, CandidateMemoryPolicy, _digest_with],
    ids=["provenance", "artifact", "bundle", "candidate_policy", "digest"],
)
def test_unknown_fields_are_rejected_never_absorbed(builder: Any) -> None:
    with pytest.raises(ValidationError):
        builder(api_key="should-never-be-accepted")


# --------------------------------------------------------------------------- #
# Lifecycle vocabulary — the deliberate absences
# --------------------------------------------------------------------------- #
def test_intake_lifecycle_has_exactly_the_four_phase_40e_members() -> None:
    assert {member.value for member in MigrationIntakeStatus} == {
        "declared",
        "ready_for_parsing",
        "blocked",
        "quarantined",
    }


@pytest.mark.parametrize(
    "forbidden",
    [
        "parsed",
        "projected",
        "reviewed",
        "approved",
        "persisted",
        "verified",
        "imported",
        "active",
    ],
)
def test_no_post_parsing_lifecycle_state_is_representable(forbidden: str) -> None:
    # Phase 40F parses and Phase 40G is the exclusive reviewed-persistence
    # boundary. A vocabulary able to name either outcome here would let a
    # declaration claim work no code in this phase performs.
    with pytest.raises(ValueError):
        MigrationIntakeStatus(forbidden)


def test_a_bundle_cannot_declare_its_own_readiness() -> None:
    for status in (
        MigrationIntakeStatus.READY_FOR_PARSING,
        MigrationIntakeStatus.BLOCKED,
        MigrationIntakeStatus.QUARANTINED,
    ):
        with pytest.raises(ValidationError, match="intake_status must remain"):
            _bundle(intake_status=status)
    assert _bundle().intake_status is MigrationIntakeStatus.DECLARED


# --------------------------------------------------------------------------- #
# Pinned safety flags
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("field", "match"),
    [
        ("read_only", "read_only must remain True"),
        ("is_memory", "is_memory must remain False"),
        ("is_verified_evidence", "is_verified_evidence must remain False"),
    ],
)
def test_bundle_safety_flags_cannot_be_disabled(field: str, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        _bundle(**{field: field != "read_only"})


def test_bundle_safety_flags_reject_integer_truthiness() -> None:
    # ``0``/``1`` must never become a safety flag: these carry the phase's claims
    # about what a bundle is, and they must be explicit.
    with pytest.raises(ValidationError, match="flag field must be a boolean"):
        _bundle(is_memory=0)


def test_declared_digest_can_never_be_marked_verified() -> None:
    with pytest.raises(ValidationError, match="verified must remain False"):
        DeclaredArtifactDigest(
            algorithm=MigrationDigestAlgorithm.SHA256,
            value=SHA256_VALUE,
            verified=True,
        )
    assert _digest().verified is False


def test_provenance_cannot_declare_machine_acquired_or_verified_material() -> None:
    with pytest.raises(ValidationError, match="user_provided must remain True"):
        _provenance(user_provided=False)
    with pytest.raises(ValidationError, match="verified must remain False"):
        _provenance(verified=True)


# --------------------------------------------------------------------------- #
# Candidate memory policy
# --------------------------------------------------------------------------- #
def test_candidate_memory_policy_pins_the_ceiling_migrated_material_may_reach() -> None:
    policy = CANDIDATE_MEMORY_POLICY
    assert policy.lifecycle_state is LifecycleState.INACTIVE
    assert policy.verification_state is VerificationState.UNVERIFIED
    assert policy.represents_active_memory is False
    assert policy.human_review_required is True
    assert policy.persistable is False


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"lifecycle_state": LifecycleState.ACTIVE}, "must remain 'inactive'"),
        (
            {"verification_state": VerificationState.HUMAN_CONFIRMED},
            "must remain 'unverified'",
        ),
        ({"represents_active_memory": True}, "represents_active_memory must remain"),
        ({"human_review_required": False}, "human_review_required must remain True"),
        ({"persistable": True}, "persistable must remain False"),
    ],
)
def test_candidate_memory_policy_cannot_be_widened(
    override: dict[str, Any], match: str
) -> None:
    with pytest.raises(ValidationError, match=match):
        CandidateMemoryPolicy(**override)


# --------------------------------------------------------------------------- #
# Declared digest representability
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("algorithm", list(MigrationDigestAlgorithm))
def test_digest_length_matches_the_declared_algorithm(
    algorithm: MigrationDigestAlgorithm,
) -> None:
    expected = DIGEST_HEX_LENGTHS[algorithm]
    assert DeclaredArtifactDigest(algorithm=algorithm, value="f" * expected)
    with pytest.raises(ValidationError, match="hex characters"):
        DeclaredArtifactDigest(algorithm=algorithm, value="f" * (expected - 1))


@pytest.mark.parametrize("value", ["A" * 64, "g" * 64, "  ", "0x" + "a" * 62])
def test_digest_value_must_be_lowercase_hexadecimal(value: str) -> None:
    with pytest.raises(ValidationError):
        DeclaredArtifactDigest(
            algorithm=MigrationDigestAlgorithm.SHA256, value=value
        )


def test_sha512_digest_is_representable() -> None:
    digest = _digest(MigrationDigestAlgorithm.SHA512, SHA512_VALUE)
    assert digest.algorithm is MigrationDigestAlgorithm.SHA512


# --------------------------------------------------------------------------- #
# Identity-bearing declared paths
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path",
    [
        "../../etc/passwd",
        "/absolute/conversations.json",
        "C:/Users/someone/export.zip",
        " leading-space.json",
        "trailing-space.json ",
        "nested//double.json",
        "chat\x00null.json",
        "NUL",
        "a\\b\\c.json",
    ],
)
def test_unsafe_paths_are_representable_and_preserved_byte_for_byte(path: str) -> None:
    # The contract records; the assessment judges. Rejecting these here would
    # raise an untyped ValidationError and destroy the typed
    # blocked/quarantined diagnostics the intake boundary exists to produce —
    # and rewriting them would mutate identity-bearing material.
    assert _artifact(declared_relative_path=path).declared_relative_path == path


@pytest.mark.parametrize("path", ["", "   ", "\t\n"])
def test_unrecordable_paths_are_rejected(path: str) -> None:
    with pytest.raises(ValidationError):
        _artifact(declared_relative_path=path)


# --------------------------------------------------------------------------- #
# Bounded metadata
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "key",
    ["api_key", "content", "raw", "session_token", "API-KEY", " Password "],
)
def test_credential_and_content_metadata_keys_are_refused(key: str) -> None:
    with pytest.raises(ValidationError, match="not permitted"):
        _artifact(metadata={key: "value"})


def test_metadata_entry_count_is_bounded() -> None:
    oversized = {f"key-{index}": index for index in range(MAX_MIGRATION_METADATA_ENTRIES + 1)}
    with pytest.raises(ValidationError, match="entry limit"):
        _bundle(metadata=oversized)


def test_metadata_nesting_depth_is_bounded() -> None:
    deep: Any = "leaf"
    for _ in range(8):
        deep = {"nested": deep}
    with pytest.raises(ValidationError):
        _bundle(metadata=deep)


def test_benign_metadata_is_accepted_unchanged() -> None:
    metadata = {"export_tool": "chatgpt-data-export", "entry_count": 12}
    assert _bundle(metadata=metadata).metadata == metadata


# --------------------------------------------------------------------------- #
# Bundle composition
# --------------------------------------------------------------------------- #
def test_duplicate_artifact_identifiers_are_refused_before_assessment() -> None:
    # Ambiguous identifiers would make every per-artifact diagnostic unable to
    # say which entry it concerns, so the ambiguity is refused up front.
    with pytest.raises(ValidationError, match="duplicate artifact_id"):
        _bundle(artifacts=[_artifact(), _artifact(declared_relative_path="other.json")])


def test_declared_totals_are_not_reconciled_by_the_contract() -> None:
    # A mismatch is a meaningful intake finding, so the contract records it and
    # the assessment reports it. Enforcing it here would turn an informative
    # diagnostic into an untyped construction error.
    bundle = _bundle(declared_artifact_count=99, declared_total_byte_size=1)
    assert bundle.declared_artifact_count == 99
    assert len(bundle.artifacts) == 1


def test_normalized_orders_artifacts_without_dropping_any() -> None:
    artifacts = [
        _artifact(artifact_id="artifact-c", declared_relative_path="c.json"),
        _artifact(artifact_id="artifact-a", declared_relative_path="a.json"),
        _artifact(artifact_id="artifact-b", declared_relative_path="b.json"),
    ]
    normalized = _bundle(artifacts=artifacts).normalized()
    assert [item.artifact_id for item in normalized.artifacts] == [
        "artifact-a",
        "artifact-b",
        "artifact-c",
    ]
    assert len(normalized.artifacts) == len(artifacts)


def test_target_scope_reuses_the_active_memory_vocabulary() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="hive-mind")
    assert _bundle(target_scope=scope).target_scope == scope


# --------------------------------------------------------------------------- #
# Deterministic identity derivation
# --------------------------------------------------------------------------- #
def test_derive_migration_id_is_stable_and_input_sensitive() -> None:
    first = derive_migration_id("mm-intake", "alpha", "beta")
    assert first == derive_migration_id("mm-intake", "alpha", "beta")
    assert first != derive_migration_id("mm-intake", "beta", "alpha")
    assert first.startswith("mm-intake-")


def test_derive_migration_id_cannot_be_forged_through_delimiter_content() -> None:
    # Canonical JSON array material, not a delimiter join: a part *containing*
    # the delimiter must not be able to forge a different part boundary.
    assert derive_migration_id("mm", "a", "b") != derive_migration_id("mm", "a,b")
    assert derive_migration_id("mm", "a-", "b") != derive_migration_id("mm", "a", "-b")


def test_derive_migration_id_rejects_empty_material() -> None:
    with pytest.raises(ValueError, match="at least one input part"):
        derive_migration_id("mm-intake")


def test_artifact_fingerprint_ignores_caller_assigned_identity_and_annotation() -> None:
    base = _artifact()
    renamed = _artifact(artifact_id="artifact-renamed")
    annotated = _artifact(label="Conversations", metadata={"note": "primary"})
    assert derive_artifact_fingerprint(base) == derive_artifact_fingerprint(renamed)
    assert derive_artifact_fingerprint(base) == derive_artifact_fingerprint(annotated)


@pytest.mark.parametrize(
    "override",
    [
        {"declared_relative_path": "other.json"},
        {"entry_kind": MigrationEntryKind.DIRECTORY},
        {"artifact_format": MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT},
        {"container": MigrationContainerKind.ZIP_ARCHIVE},
        {"declared_byte_size": 4097},
        {"declared_digest": _digest(MigrationDigestAlgorithm.SHA512, SHA512_VALUE)},
        {"declared_modified_at": EXPORTED_AT},
    ],
)
def test_artifact_fingerprint_tracks_every_material_field(
    override: dict[str, Any]
) -> None:
    assert derive_artifact_fingerprint(_artifact()) != derive_artifact_fingerprint(
        _artifact(**override)
    )


def test_bundle_fingerprint_is_independent_of_artifact_declaration_order() -> None:
    # Reordering the same declared artifacts does not change what the user handed
    # over — the deliberate opposite of the Phase 40C packet identity, where
    # evidence order encodes assembler ranking and is therefore material.
    first = _artifact(artifact_id="artifact-a", declared_relative_path="a.json")
    second = _artifact(artifact_id="artifact-b", declared_relative_path="b.json")
    assert derive_bundle_fingerprint(
        _bundle(artifacts=[first, second])
    ) == derive_bundle_fingerprint(_bundle(artifacts=[second, first]))


def test_bundle_fingerprint_ignores_the_caller_assigned_bundle_id() -> None:
    assert derive_bundle_fingerprint(_bundle()) == derive_bundle_fingerprint(
        _bundle(bundle_id="bundle-renamed")
    )


@pytest.mark.parametrize(
    "override",
    [
        {"provenance": _provenance(custody=MigrationCustodyKind.USER_ASSEMBLED_BUNDLE)},
        {"artifacts": [_artifact(declared_byte_size=1)]},
        {"declared_at": EXPORTED_AT},
        {
            "target_scope": MemoryScope(
                scope_type=MemoryScopeType.PROJECT, scope_id="hive-mind"
            )
        },
    ],
)
def test_bundle_fingerprint_tracks_every_material_field(
    override: dict[str, Any]
) -> None:
    assert derive_bundle_fingerprint(_bundle()) != derive_bundle_fingerprint(
        _bundle(**override)
    )


def test_fingerprint_helpers_are_exposed_on_the_records_themselves() -> None:
    artifact = _artifact()
    bundle = _bundle(artifacts=[artifact])
    assert artifact.fingerprint() == derive_artifact_fingerprint(artifact)
    assert bundle.fingerprint() == derive_bundle_fingerprint(bundle)


# --------------------------------------------------------------------------- #
# Assessment result contracts
# --------------------------------------------------------------------------- #
def _diagnostic(
    code: MigrationDiagnosticCode, message: str = "finding"
) -> MigrationIntakeDiagnostic:
    return MigrationIntakeDiagnostic(code=code, message=message, subject_id="bundle-1")


def _assessment(**overrides: Any) -> MemoryMigrationIntakeAssessment:
    fields: dict[str, Any] = {
        "bundle_id": "bundle-1",
        "bundle_fingerprint": "mm-bundle-0123456789abcdef01234567",
        "declared_status": MigrationIntakeStatus.DECLARED,
        "assessed_status": MigrationIntakeStatus.READY_FOR_PARSING,
        "ready_for_parsing": True,
        "artifact_count": 1,
    }
    fields.update(overrides)
    return MemoryMigrationIntakeAssessment(**fields)


def test_every_diagnostic_code_has_exactly_one_fixed_severity() -> None:
    assert set(MIGRATION_DIAGNOSTIC_SEVERITY) == set(MigrationDiagnosticCode)


def test_diagnostic_severity_is_filled_in_from_the_code() -> None:
    for code, expected in MIGRATION_DIAGNOSTIC_SEVERITY.items():
        assert _diagnostic(code).severity is expected


def test_diagnostic_severity_cannot_be_reclassified_at_the_call_site() -> None:
    with pytest.raises(ValidationError, match="cannot be reclassified"):
        MigrationIntakeDiagnostic(
            code=MigrationDiagnosticCode.UNSAFE_ENTRY_KIND,
            severity=MigrationDiagnosticSeverity.ADVISORY,
            message="downgrade attempt",
        )


def test_only_the_unverified_digest_notice_is_advisory() -> None:
    advisory = {
        code
        for code, severity in MIGRATION_DIAGNOSTIC_SEVERITY.items()
        if severity is MigrationDiagnosticSeverity.ADVISORY
    }
    assert advisory == {MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED}


def test_resolve_intake_status_escalates_to_the_single_most_severe_finding() -> None:
    assert resolve_intake_status([]) is MigrationIntakeStatus.READY_FOR_PARSING
    assert (
        resolve_intake_status([MigrationDiagnosticSeverity.ADVISORY])
        is MigrationIntakeStatus.READY_FOR_PARSING
    )
    assert (
        resolve_intake_status(
            [MigrationDiagnosticSeverity.ADVISORY, MigrationDiagnosticSeverity.BLOCKING]
        )
        is MigrationIntakeStatus.BLOCKED
    )
    assert (
        resolve_intake_status(
            [
                MigrationDiagnosticSeverity.BLOCKING,
                MigrationDiagnosticSeverity.QUARANTINE,
                MigrationDiagnosticSeverity.ADVISORY,
            ]
        )
        is MigrationIntakeStatus.QUARANTINED
    )


def test_assessment_status_cannot_disagree_with_its_diagnostics() -> None:
    with pytest.raises(ValidationError, match="disagrees with the status implied"):
        _assessment(
            diagnostics=[_diagnostic(MigrationDiagnosticCode.UNSAFE_ENTRY_KIND)],
            assessed_status=MigrationIntakeStatus.BLOCKED,
            ready_for_parsing=False,
        )


def test_assessment_ready_flag_is_bound_to_the_status() -> None:
    with pytest.raises(ValidationError, match="if and only if"):
        _assessment(ready_for_parsing=False)


def test_assessment_can_never_conclude_declared() -> None:
    with pytest.raises(ValidationError, match="must not be 'declared'"):
        _assessment(
            assessed_status=MigrationIntakeStatus.DECLARED, ready_for_parsing=False
        )


def test_assessment_cannot_claim_artifacts_were_read() -> None:
    with pytest.raises(ValidationError, match="artifacts_read must remain False"):
        _assessment(artifacts_read=True)


def test_empty_bundle_can_never_be_assessed_ready() -> None:
    with pytest.raises(ValidationError, match="cannot be ready for parsing"):
        _assessment(artifact_count=0)


def test_assessment_diagnostics_must_be_unique_and_canonically_ordered() -> None:
    duplicate = _diagnostic(MigrationDiagnosticCode.EMPTY_BUNDLE)
    with pytest.raises(ValidationError, match="duplicate diagnostic"):
        _assessment(
            diagnostics=[duplicate, duplicate],
            assessed_status=MigrationIntakeStatus.BLOCKED,
            ready_for_parsing=False,
        )
    out_of_order = [
        _diagnostic(MigrationDiagnosticCode.MISSING_DECLARED_SIZE),
        _diagnostic(MigrationDiagnosticCode.EMPTY_BUNDLE),
    ]
    with pytest.raises(ValidationError, match="canonical order"):
        _assessment(
            diagnostics=out_of_order,
            assessed_status=MigrationIntakeStatus.BLOCKED,
            ready_for_parsing=False,
        )


def test_permits_parsing_requires_readiness_and_a_matching_fingerprint() -> None:
    ready = _assessment()
    assert ready.permits_parsing(bundle_fingerprint=ready.bundle_fingerprint) is True
    # An assessment of a since-edited declaration permits nothing, however
    # favourable its verdict — the check Phase 40F must make before parsing.
    assert ready.permits_parsing(bundle_fingerprint="mm-bundle-different") is False

    blocked = _assessment(
        diagnostics=[_diagnostic(MigrationDiagnosticCode.EMPTY_BUNDLE)],
        assessed_status=MigrationIntakeStatus.BLOCKED,
        ready_for_parsing=False,
    )
    assert blocked.permits_parsing(bundle_fingerprint=blocked.bundle_fingerprint) is False


def test_assessment_partitions_its_diagnostics_by_severity() -> None:
    report = _assessment(
        diagnostics=sorted(
            [
                _diagnostic(MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED),
                _diagnostic(MigrationDiagnosticCode.EMPTY_BUNDLE),
                _diagnostic(MigrationDiagnosticCode.UNSAFE_ENTRY_KIND),
            ],
            key=lambda item: item.sort_key(),
        ),
        assessed_status=MigrationIntakeStatus.QUARANTINED,
        ready_for_parsing=False,
    )
    assert [item.code for item in report.quarantine_diagnostics] == [
        MigrationDiagnosticCode.UNSAFE_ENTRY_KIND
    ]
    assert [item.code for item in report.blocking_diagnostics] == [
        MigrationDiagnosticCode.EMPTY_BUNDLE
    ]
    assert [item.code for item in report.advisory_diagnostics] == [
        MigrationDiagnosticCode.DECLARED_DIGEST_UNVERIFIED
    ]


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
    "run",
    "urlopen",
    "system",
    "popen",
    "extractall",
    "listdir",
    "walk",
}
_FORBIDDEN_IMPORTS = {
    "os",
    "random",
    "secrets",
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


def test_contract_module_performs_no_clock_random_io_or_archive_access() -> None:
    tree = ast.parse(Path(inspect.getfile(mm_module)).read_text(encoding="utf-8"))
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
