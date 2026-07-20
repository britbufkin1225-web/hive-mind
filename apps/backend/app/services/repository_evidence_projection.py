"""Phase 39A — deterministic Repository Evidence Projection service.

A pure, read-only transformation from existing Repository Observer results
(``RepositorySnapshot`` + optional ``RepositoryDriftAnalysis``) into bounded
Active Memory *candidate* records and *evidence* records. The same validated
input always produces equivalent serialized output.

This service never: invokes Git, touches the filesystem, reads a clock,
persists anything, inserts into an Active Memory store, resolves
contradictions, calculates active state, deduplicates against a store, uses
AI/LLM interpretation, or exposes an endpoint.

Settled design decisions (Phase 39A corrections applied to the scout report):

* **Timestamps** come only from the inputs. ``snapshot.observed_at`` is the
  observation time *and* the deterministic ``created_at`` of every candidate
  produced by this projection (a projection has no clock of its own, so the
  only truthful, reproducible creation time is the observation it projects).
  Evidence ``captured_at`` prefers the observer item's own capture time.
  ``valid_until`` is always ``None`` — no validity duration is invented.
  Naive datetimes are serialized as-is via ISO format for hashing; they are
  never normalized through the host-local timezone.
* **Identifiers** are content-derived via canonical JSON + SHA-256 (the
  drift service's private helper uses SHA-1, so it is deliberately not
  reused). No UUIDs, no ``hash()``, no wall clock, no input-order dependence.
  A duplicate generated id raises :class:`ProjectionDuplicateIdError` instead
  of silently collapsing records.
* **Verification is claim-dependent, never automatic.** Git-derived evidence
  is not auto-trusted: ``verified`` requires a verified repository identity,
  a direct observation, and no warning/limitation undermining that specific
  claim; partial snapshots or relevant observer warnings downgrade to
  ``partially_verified``; an unverified identity leaves every claim
  ``unverified``. ``confidence`` is never set. ``LifecycleState.ACTIVE`` on a
  candidate means only "successfully projected" — active-state selection is a
  later, separate concern.
* **Identity gating.** ``unsafe_location``, ``mismatched_root``, and
  ``mismatched_remote`` identity statuses block projection with a fatal
  domain error (untrustworthy scoping must not manufacture records). A
  detached HEAD is an observed ``operation_state`` value, never fatal.
* **No per-file records.** Changed files are summarized as bounded, sorted
  path lists (with explicit omitted counts) inside evidence metadata; no
  per-file ``MemoryRecord`` or per-file ``EvidenceRecord`` is ever created,
  so file-count growth cannot flood the projection.
* **Candidate retention priority** (documented, deterministic): core
  identity/state claims are ordered — and, under overflow, retained — before
  optional aggregates. See :data:`_CANDIDATE_PRIORITY`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from app.models.active_memory import (
    ClaimValueKind,
    EvidenceRecord,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceType,
    LifecycleState,
    MemoryClaim,
    MemoryRecord,
    MemoryRecordKind,
    MemoryScope,
    MemoryScopeType,
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models.repository_evidence_projection import (
    REPOSITORY_EVIDENCE_PROJECTION_SERVICE_VERSION,
    ProjectionOverflow,
    ProjectionOverflowKind,
    RepositoryEvidenceProjectionLimits,
    RepositoryEvidenceProjectionRequest,
    RepositoryEvidenceProjectionResult,
)
from app.models.repository_observer import (
    REPOSITORY_OBSERVER_CONTRACT_VERSION,
    ObserverWarningCategory,
    RepositoryDriftAnalysis,
    RepositoryIdentityStatus,
    RepositoryOperationState,
    RepositorySnapshot,
    SnapshotCompleteness,
    WorkingTreeState,
    WorkingTreeStatus,
)


# --------------------------------------------------------------------------- #
# Domain errors
# --------------------------------------------------------------------------- #
class RepositoryEvidenceProjectionError(Exception):
    """Base class for fatal projection failures."""


class ProjectionContractVersionError(RepositoryEvidenceProjectionError):
    """Raised for an unsupported Repository Observer contract version."""


class ProjectionIdentityError(RepositoryEvidenceProjectionError):
    """Raised when repository identity is unsafe or mismatched — projecting
    candidates under an untrustworthy scope would fabricate authority."""


class ProjectionInputMismatchError(RepositoryEvidenceProjectionError):
    """Raised when the drift analysis does not belong to the snapshot's
    repository."""


class ProjectionTimestampError(RepositoryEvidenceProjectionError):
    """Raised when a required observation timestamp is absent or invalid."""


class ProjectionDuplicateIdError(RepositoryEvidenceProjectionError):
    """Raised when two generated outputs collide on a deterministic id."""


# --------------------------------------------------------------------------- #
# Deterministic vocabularies
# --------------------------------------------------------------------------- #
# Identity statuses that make scoping untrustworthy: fatal, never projected.
_FATAL_IDENTITY_STATUSES = frozenset(
    {
        RepositoryIdentityStatus.UNSAFE_LOCATION,
        RepositoryIdentityStatus.MISMATCHED_ROOT,
        RepositoryIdentityStatus.MISMATCHED_REMOTE,
    }
)

# Closed candidate claim vocabulary, in documented retention-priority order:
# core repository identity/state first, optional aggregates last. Under
# candidate overflow the head of this order is retained.
_CANDIDATE_PRIORITY: tuple[str, ...] = (
    "identity_status",
    "current_commit",
    "current_branch",
    "working_tree_state",
    "operation_state",
    "snapshot_completeness",
    "upstream_reference",
    "default_branch",
    "drift_status",
    "staged_count",
    "unstaged_count",
    "untracked_count",
    "conflicted_count",
    "drifted_file_count",
)

_METADATA_CLAIMS = frozenset(
    {
        "identity_status",
        "current_commit",
        "current_branch",
        "operation_state",
        "upstream_reference",
        "default_branch",
    }
)
_WORKING_TREE_CLAIMS = frozenset(
    {
        "working_tree_state",
        "staged_count",
        "unstaged_count",
        "untracked_count",
        "conflicted_count",
    }
)
_DRIFT_CLAIMS = frozenset({"drift_status", "drifted_file_count"})

# Observer warning categories that undermine specific claim families. A
# warning only downgrades the claims it actually weakens (Phase 39A §7).
_METADATA_UNDERMINING_WARNINGS = frozenset(
    {
        ObserverWarningCategory.GIT_METADATA_UNAVAILABLE,
        ObserverWarningCategory.TIMESTAMP_AMBIGUITY,
    }
)
_WORKING_TREE_UNDERMINING_WARNINGS = frozenset(
    {
        ObserverWarningCategory.PARTIAL_SNAPSHOT,
        ObserverWarningCategory.FILE_LIMIT_REACHED,
        ObserverWarningCategory.BYTE_LIMIT_REACHED,
        ObserverWarningCategory.EVIDENCE_LIMIT_REACHED,
        ObserverWarningCategory.EVIDENCE_TRUNCATED,
    }
)

_DIRTY_WORKING_TREE_STATES = frozenset(
    {
        WorkingTreeState.MODIFIED,
        WorkingTreeState.STAGED,
        WorkingTreeState.UNTRACKED,
        WorkingTreeState.CONFLICTED,
    }
)

# Worst-first completeness ranking used to combine snapshot/drift/overflow
# into one result completeness.
_COMPLETENESS_RANK: dict[SnapshotCompleteness, int] = {
    SnapshotCompleteness.COMPLETE: 0,
    SnapshotCompleteness.PARTIAL: 1,
    SnapshotCompleteness.UNAVAILABLE: 2,
    SnapshotCompleteness.INVALID: 3,
    SnapshotCompleteness.REJECTED: 4,
}


# --------------------------------------------------------------------------- #
# Deterministic id helper (canonical JSON + SHA-256; Phase 39A §8)
# --------------------------------------------------------------------------- #
def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _canonical_datetime(value: datetime) -> str:
    # Stable ISO serialization for hashing. Naive datetimes serialize as-is —
    # they are never reinterpreted through the host-local timezone.
    return value.isoformat()


class RepositoryEvidenceProjectionService:
    """Project Repository Observer results into Active Memory candidates.

    Stateless: the service retains nothing between calls, and every output
    model is freshly constructed, so caller mutation of a result can never
    alter a subsequent projection.
    """

    def project(
        self, request: RepositoryEvidenceProjectionRequest
    ) -> RepositoryEvidenceProjectionResult:
        snapshot = request.snapshot
        drift = request.drift_analysis
        limits = request.limits

        self._validate_contract_versions(snapshot, drift)
        self._validate_timestamps(snapshot, drift)
        self._validate_identity(snapshot, drift)

        identity = snapshot.repository_identity
        repository_id = identity.repository_id
        observed_at = snapshot.observed_at
        scope = MemoryScope(
            scope_type=MemoryScopeType.REPOSITORY, scope_id=repository_id
        )
        source = MemorySource(
            source_type=MemorySourceType.REPOSITORY_OBSERVER,
            source_id=f"repository-observer:{snapshot.observer_version}",
        )

        warnings: list[str] = []
        skipped: list[str] = []
        overflow: list[ProjectionOverflow] = []

        evidence_by_id, anchors = self._build_evidence(
            snapshot=snapshot,
            drift=drift,
            limits=limits,
            repository_id=repository_id,
            observed_at=observed_at,
            scope=scope,
            source=source,
            skipped=skipped,
            overflow=overflow,
        )
        candidates_by_id = self._build_candidates(
            request=request,
            anchors=anchors,
            scope=scope,
            source=source,
            skipped=skipped,
        )

        warnings.extend(
            f"observer-warning {item.warning_id} ({item.category.value})"
            for item in snapshot.warnings
        )
        if drift is not None:
            warnings.extend(
                f"drift-warning {item.warning_id} ({item.category.value})"
                for item in drift.warnings
            )

        evidence_records = self._ordered_evidence(evidence_by_id.values(), anchors)
        candidate_records = self._ordered_candidates(candidates_by_id.values())
        warnings = sorted(warnings)
        skipped = sorted(skipped)

        evidence_records, evidence_overflow = self._bounded(
            evidence_records,
            limits.max_evidence_records,
            ProjectionOverflowKind.EVIDENCE_RECORD_COUNT,
            "core anchors first, then observer evidence by type/kind/value/id",
        )
        candidate_records, candidate_overflow = self._bounded(
            candidate_records,
            limits.max_candidate_records,
            ProjectionOverflowKind.CANDIDATE_RECORD_COUNT,
            "documented candidate priority order (core state before aggregates)",
        )
        warnings, warning_overflow = self._bounded(
            warnings,
            limits.max_warnings,
            ProjectionOverflowKind.WARNING_COUNT,
            "lexicographic warning order",
        )
        skipped, skipped_overflow = self._bounded(
            skipped,
            limits.max_skipped_observations,
            ProjectionOverflowKind.SKIPPED_OBSERVATION_COUNT,
            "lexicographic skipped-observation order",
        )
        overflow.extend(
            item
            for item in (
                evidence_overflow,
                candidate_overflow,
                warning_overflow,
                skipped_overflow,
            )
            if item is not None
        )
        overflow.sort(key=lambda item: (item.kind.value, item.overflow_id))

        completeness = self._result_completeness(snapshot, drift, overflow)

        return RepositoryEvidenceProjectionResult(
            projection_id=_stable_id(
                "projection",
                {
                    "project_id": request.project_id,
                    "repository_id": repository_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "observed_at": _canonical_datetime(observed_at),
                    "drift_id": drift.drift_id if drift is not None else None,
                },
            ),
            projection_version=REPOSITORY_EVIDENCE_PROJECTION_SERVICE_VERSION,
            project_id=request.project_id,
            repository_id=repository_id,
            source_snapshot_id=snapshot.snapshot_id,
            source_drift_id=drift.drift_id if drift is not None else None,
            evidence_records=evidence_records,
            candidate_records=candidate_records,
            warnings=warnings,
            skipped_observations=skipped,
            completeness=completeness,
            overflow=overflow,
            read_only=True,
        )

    # ------------------------------------------------------------------ #
    # Fatal validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_contract_versions(
        snapshot: RepositorySnapshot, drift: RepositoryDriftAnalysis | None
    ) -> None:
        if snapshot.contract_version != REPOSITORY_OBSERVER_CONTRACT_VERSION:
            raise ProjectionContractVersionError(
                f"unsupported snapshot contract version {snapshot.contract_version!r}; "
                f"expected {REPOSITORY_OBSERVER_CONTRACT_VERSION!r}"
            )
        if drift is not None and drift.contract_version != (
            REPOSITORY_OBSERVER_CONTRACT_VERSION
        ):
            raise ProjectionContractVersionError(
                f"unsupported drift contract version {drift.contract_version!r}; "
                f"expected {REPOSITORY_OBSERVER_CONTRACT_VERSION!r}"
            )

    @staticmethod
    def _validate_timestamps(
        snapshot: RepositorySnapshot, drift: RepositoryDriftAnalysis | None
    ) -> None:
        # Guards models built via ``model_construct`` (validation bypassed):
        # without an observation timestamp there is no deterministic time base.
        if not isinstance(snapshot.observed_at, datetime):
            raise ProjectionTimestampError(
                "snapshot.observed_at is required; the projection has no clock"
            )
        if drift is not None and not isinstance(drift.observed_at, datetime):
            raise ProjectionTimestampError(
                "drift_analysis.observed_at is required; the projection has no clock"
            )

    @staticmethod
    def _validate_identity(
        snapshot: RepositorySnapshot, drift: RepositoryDriftAnalysis | None
    ) -> None:
        identity = snapshot.repository_identity
        if identity.status in _FATAL_IDENTITY_STATUSES:
            raise ProjectionIdentityError(
                f"repository identity status {identity.status.value!r} prevents "
                "trustworthy scoping; refusing to project candidates"
            )
        if drift is not None:
            drift_identity = drift.repository_identity
            if drift_identity.repository_id != identity.repository_id:
                raise ProjectionInputMismatchError(
                    "drift analysis repository "
                    f"{drift_identity.repository_id!r} does not match snapshot "
                    f"repository {identity.repository_id!r}"
                )
            if drift_identity.status in _FATAL_IDENTITY_STATUSES:
                raise ProjectionIdentityError(
                    f"drift repository identity status {drift_identity.status.value!r} "
                    "prevents trustworthy scoping; refusing to project candidates"
                )

    # ------------------------------------------------------------------ #
    # Evidence projection
    # ------------------------------------------------------------------ #
    def _build_evidence(
        self,
        *,
        snapshot: RepositorySnapshot,
        drift: RepositoryDriftAnalysis | None,
        limits: RepositoryEvidenceProjectionLimits,
        repository_id: str,
        observed_at: datetime,
        scope: MemoryScope,
        source: MemorySource,
        skipped: list[str],
        overflow: list[ProjectionOverflow],
    ) -> tuple[dict[str, EvidenceRecord], dict[str, str]]:
        """Return (evidence records by id, anchor name -> evidence id).

        Anchors are the handful of core evidence records candidates cite:
        ``snapshot``, ``commit``, ``branch``, ``remote``, ``drift``.
        """
        identity = snapshot.repository_identity
        by_id: dict[str, EvidenceRecord] = {}
        anchors: dict[str, str] = {}

        def register(record: EvidenceRecord, anchor: str | None = None) -> None:
            existing = by_id.get(record.evidence_id)
            if existing is not None:
                raise ProjectionDuplicateIdError(
                    f"duplicate projected evidence id {record.evidence_id!r}"
                )
            by_id[record.evidence_id] = record
            if anchor is not None:
                anchors[anchor] = record.evidence_id

        def make(
            *,
            evidence_type: EvidenceType,
            reference_kind: EvidenceReferenceKind,
            reference_value: str,
            captured_at: datetime,
            summary: str,
            metadata: dict[str, object],
            detail: str | None = None,
        ) -> EvidenceRecord:
            evidence_id = _stable_id(
                "evidence",
                {
                    "repository_id": repository_id,
                    "evidence_type": evidence_type.value,
                    "reference_kind": reference_kind.value,
                    "reference_value": reference_value,
                    "captured_at": _canonical_datetime(captured_at),
                    "source_id": source.source_id,
                },
            )
            return EvidenceRecord(
                evidence_id=evidence_id,
                evidence_type=evidence_type,
                reference=EvidenceReference(
                    reference_kind=reference_kind,
                    value=reference_value,
                    detail=detail,
                ),
                scope=scope.model_copy(deep=True),
                source=source.model_copy(deep=True),
                captured_at=captured_at,
                valid_until=None,
                summary=summary,
                metadata=metadata,
            )

        # Snapshot anchor: the repository status result itself, carrying the
        # bounded structured state every snapshot-derived candidate cites.
        paths = sorted(item.normalized_path for item in snapshot.changed_files)
        retained_paths = paths[: limits.max_file_path_summary_items]
        if len(paths) > len(retained_paths):
            skipped.append(
                "changed_file_paths: "
                f"{len(paths) - len(retained_paths)} of {len(paths)} paths omitted "
                "from the bounded snapshot file-path summary"
            )
            overflow.append(
                ProjectionOverflow(
                    overflow_id="overflow-file-path-summary-snapshot",
                    kind=ProjectionOverflowKind.FILE_PATH_SUMMARY_COUNT,
                    configured_limit=limits.max_file_path_summary_items,
                    observed_count=len(paths),
                    retained_count=len(retained_paths),
                    omitted_count=len(paths) - len(retained_paths),
                    deterministic_cutoff="first N normalized paths in lexicographic order",
                )
            )
        register(
            make(
                evidence_type=EvidenceType.REPOSITORY_COMMAND_OUTPUT,
                reference_kind=EvidenceReferenceKind.SOURCE_RECORD_ID,
                reference_value=snapshot.snapshot_id,
                captured_at=observed_at,
                summary="Repository Observer snapshot status result.",
                metadata={
                    "observer_version": snapshot.observer_version,
                    "completeness": snapshot.completeness.value,
                    "operation_state": identity.operation_state.value,
                    "identity_status": identity.status.value,
                    "working_tree_states": sorted(
                        state.value for state in snapshot.working_tree.states
                    ),
                    "staged_count": snapshot.working_tree.staged_count,
                    "unstaged_count": snapshot.working_tree.unstaged_count,
                    "untracked_count": snapshot.working_tree.untracked_count,
                    "conflicted_count": snapshot.working_tree.conflicted_count,
                    "changed_file_count": len(snapshot.changed_files),
                    "changed_file_paths": retained_paths,
                    "changed_file_paths_omitted": len(paths) - len(retained_paths),
                    "truncated": any(item.truncated for item in snapshot.overflow),
                    "warning_ids": sorted(
                        item.warning_id for item in snapshot.warnings
                    )[: limits.max_warnings],
                },
            ),
            anchor="snapshot",
        )

        commit = snapshot.commit or identity.current_commit
        if commit is not None:
            register(
                make(
                    evidence_type=EvidenceType.COMMIT,
                    reference_kind=EvidenceReferenceKind.COMMIT_HASH,
                    reference_value=commit,
                    captured_at=observed_at,
                    summary="Current commit observed by the Repository Observer.",
                    metadata={"identity_status": identity.status.value},
                ),
                anchor="commit",
            )
        else:
            skipped.append(
                "current_commit: omitted (no commit observed; e.g. unborn repository)"
            )

        branch = snapshot.branch or identity.current_branch
        if branch is not None:
            register(
                make(
                    evidence_type=EvidenceType.BRANCH,
                    reference_kind=EvidenceReferenceKind.BRANCH_NAME,
                    reference_value=branch,
                    captured_at=observed_at,
                    summary="Current branch observed by the Repository Observer.",
                    metadata={"identity_status": identity.status.value},
                ),
                anchor="branch",
            )
        else:
            skipped.append("current_branch: omitted (no branch observed)")

        remote = identity.primary_remote_url
        if remote is None:
            skipped.append("configured_remote: omitted (no primary remote configured)")
        elif "@" in remote.split("://", 1)[-1].split("/", 1)[0]:
            # A remote URL whose authority component carries userinfo may embed
            # credentials; a reference must never be secret-bearing.
            skipped.append(
                "configured_remote: omitted (remote URL contains userinfo and may "
                "embed credentials)"
            )
        else:
            register(
                make(
                    evidence_type=EvidenceType.REPOSITORY_COMMAND_OUTPUT,
                    reference_kind=EvidenceReferenceKind.EXTERNAL_SOURCE_ID,
                    reference_value=remote,
                    captured_at=observed_at,
                    summary="Primary configured remote observed by the Repository Observer.",
                    metadata={"identity_status": identity.status.value},
                ),
                anchor="remote",
            )

        # One bounded evidence record per observer evidence item (never file
        # contents; the reference is the observer's own capture identifier).
        for item in snapshot.evidence:
            metadata: dict[str, object] = {
                "observer_authority": item.authority.value,
                "observer_category": item.category.value,
                "truncation_state": item.truncation_state.value,
            }
            if item.repository_relative_path is not None:
                metadata["repository_relative_path"] = item.repository_relative_path
            register(
                make(
                    evidence_type=EvidenceType.REPOSITORY_COMMAND_OUTPUT,
                    reference_kind=EvidenceReferenceKind.COMMAND_ID,
                    reference_value=item.evidence_id,
                    captured_at=item.captured_at or observed_at,
                    summary=item.summary,
                    metadata=metadata,
                    detail=item.category.value,
                )
            )

        if drift is not None:
            drift_paths = sorted(item.normalized_path for item in drift.files)
            retained_drift_paths = drift_paths[: limits.max_file_path_summary_items]
            if len(drift_paths) > len(retained_drift_paths):
                skipped.append(
                    "drift_changed_file_paths: "
                    f"{len(drift_paths) - len(retained_drift_paths)} of "
                    f"{len(drift_paths)} paths omitted from the bounded drift "
                    "file-path summary"
                )
                overflow.append(
                    ProjectionOverflow(
                        overflow_id="overflow-file-path-summary-drift",
                        kind=ProjectionOverflowKind.FILE_PATH_SUMMARY_COUNT,
                        configured_limit=limits.max_file_path_summary_items,
                        observed_count=len(drift_paths),
                        retained_count=len(retained_drift_paths),
                        omitted_count=len(drift_paths) - len(retained_drift_paths),
                        deterministic_cutoff="first N normalized paths in lexicographic order",
                    )
                )
            register(
                make(
                    evidence_type=EvidenceType.REPOSITORY_COMMAND_OUTPUT,
                    reference_kind=EvidenceReferenceKind.COMMAND_ID,
                    reference_value=drift.drift_id,
                    captured_at=drift.observed_at,
                    summary="Repository Observer drift analysis result.",
                    metadata={
                        "drift_status": drift.drift_status.value,
                        "completeness": drift.completeness.value,
                        "baseline_reference": drift.baseline_reference,
                        "total_changed_files": drift.summary.total_changed_files,
                        "retained_file_count": drift.summary.retained_file_count,
                        "changed_file_paths": retained_drift_paths,
                        "changed_file_paths_omitted": (
                            len(drift_paths) - len(retained_drift_paths)
                        ),
                    },
                ),
                anchor="drift",
            )

        return by_id, anchors

    # ------------------------------------------------------------------ #
    # Candidate projection
    # ------------------------------------------------------------------ #
    def _build_candidates(
        self,
        *,
        request: RepositoryEvidenceProjectionRequest,
        anchors: dict[str, str],
        scope: MemoryScope,
        source: MemorySource,
        skipped: list[str],
    ) -> dict[str, MemoryRecord]:
        snapshot = request.snapshot
        drift = request.drift_analysis
        identity = snapshot.repository_identity
        repository_id = identity.repository_id
        observed_at = snapshot.observed_at
        by_id: dict[str, MemoryRecord] = {}

        def snapshot_refs(*extra_anchors: str) -> list[str]:
            names = ("snapshot", *extra_anchors)
            return sorted({anchors[name] for name in names if name in anchors})

        def add(
            claim_key: str,
            value: str,
            value_kind: ClaimValueKind,
            evidence_ids: list[str],
            extra_metadata: dict[str, object] | None = None,
        ) -> None:
            record_id = _stable_id(
                "candidate",
                {
                    "project_id": request.project_id,
                    "scope_id": scope.scope_id,
                    "subject": repository_id,
                    "predicate": claim_key,
                    "value": value,
                    "observed_at": _canonical_datetime(observed_at),
                    "source_id": source.source_id,
                },
            )
            if record_id in by_id:
                raise ProjectionDuplicateIdError(
                    f"duplicate projected candidate id {record_id!r}"
                )
            metadata: dict[str, object] = {"source_snapshot_id": snapshot.snapshot_id}
            if extra_metadata:
                metadata.update(extra_metadata)
            by_id[record_id] = MemoryRecord(
                record_id=record_id,
                kind=MemoryRecordKind.REPOSITORY_STATE,
                claim=MemoryClaim(
                    subject=repository_id,
                    predicate=claim_key,
                    value=value,
                    value_kind=value_kind,
                ),
                project_id=request.project_id,
                scope=scope.model_copy(deep=True),
                source=source.model_copy(deep=True),
                verification_state=self._claim_verification(claim_key, snapshot, drift),
                lifecycle_state=LifecycleState.ACTIVE,
                confidence=None,
                evidence_ids=evidence_ids,
                observed_at=observed_at,
                created_at=observed_at,
                metadata=metadata,
            )

        add(
            "identity_status",
            identity.status.value,
            ClaimValueKind.ENUM,
            snapshot_refs("remote"),
        )

        commit = snapshot.commit or identity.current_commit
        if commit is not None:
            add("current_commit", commit, ClaimValueKind.IDENTIFIER, snapshot_refs("commit"))

        branch = snapshot.branch or identity.current_branch
        if branch is not None:
            add("current_branch", branch, ClaimValueKind.IDENTIFIER, snapshot_refs("branch"))

        tree_state = self._working_tree_value(snapshot.working_tree)
        if tree_state is None:
            skipped.append(
                "working_tree_state: omitted (working tree state unavailable)"
            )
        else:
            add("working_tree_state", tree_state, ClaimValueKind.ENUM, snapshot_refs())

        if identity.operation_state is RepositoryOperationState.UNKNOWN:
            skipped.append("operation_state: omitted (operation state unknown)")
        else:
            add(
                "operation_state",
                identity.operation_state.value,
                ClaimValueKind.ENUM,
                snapshot_refs(),
            )

        add(
            "snapshot_completeness",
            snapshot.completeness.value,
            ClaimValueKind.ENUM,
            snapshot_refs(),
        )

        if identity.upstream_reference is None:
            skipped.append("upstream_reference: omitted (no upstream configured)")
        else:
            add(
                "upstream_reference",
                identity.upstream_reference,
                ClaimValueKind.IDENTIFIER,
                snapshot_refs("branch"),
            )

        if identity.default_branch is None:
            skipped.append("default_branch: omitted (default branch unknown)")
        else:
            add(
                "default_branch",
                identity.default_branch,
                ClaimValueKind.IDENTIFIER,
                snapshot_refs(),
            )

        if drift is None:
            skipped.append("drift_status: omitted (no drift analysis supplied)")
        else:
            drift_meta = {"source_drift_id": drift.drift_id}
            add(
                "drift_status",
                drift.drift_status.value,
                ClaimValueKind.ENUM,
                snapshot_refs("drift"),
                extra_metadata=drift_meta,
            )
            add(
                "drifted_file_count",
                str(drift.summary.total_changed_files),
                ClaimValueKind.INTEGER,
                snapshot_refs("drift"),
                extra_metadata=drift_meta,
            )

        if tree_state is not None:
            tree = snapshot.working_tree
            for claim_key, count in (
                ("staged_count", tree.staged_count),
                ("unstaged_count", tree.unstaged_count),
                ("untracked_count", tree.untracked_count),
                ("conflicted_count", tree.conflicted_count),
            ):
                add(claim_key, str(count), ClaimValueKind.INTEGER, snapshot_refs())

        return by_id

    # ------------------------------------------------------------------ #
    # Deterministic mappings and policies
    # ------------------------------------------------------------------ #
    @staticmethod
    def _working_tree_value(tree: WorkingTreeStatus) -> str | None:
        """Map ``WorkingTreeStatus`` to the contradiction-compatible
        clean/dirty vocabulary; ``None`` means "omit the candidate"."""
        states = set(tree.states)
        dirty_counts = (
            tree.staged_count
            + tree.unstaged_count
            + tree.untracked_count
            + tree.conflicted_count
        )
        if states & _DIRTY_WORKING_TREE_STATES or dirty_counts > 0:
            return "dirty"
        if WorkingTreeState.CLEAN in states:
            return "clean"
        # Only unavailable/unknown observations remain: insufficient evidence.
        return None

    @staticmethod
    def _claim_verification(
        claim_key: str,
        snapshot: RepositorySnapshot,
        drift: RepositoryDriftAnalysis | None,
    ) -> VerificationState:
        """Claim-dependent verification policy (Phase 39A §7).

        Never automatic: ``verified`` requires a verified identity and no
        warning/completeness limitation undermining the specific claim.
        """
        if snapshot.repository_identity.status is not RepositoryIdentityStatus.VERIFIED:
            return VerificationState.UNVERIFIED

        warning_categories = {item.category for item in snapshot.warnings}

        if claim_key in _DRIFT_CLAIMS:
            if drift is None:
                return VerificationState.UNVERIFIED
            if drift.completeness is SnapshotCompleteness.COMPLETE:
                return VerificationState.VERIFIED
            if drift.completeness is SnapshotCompleteness.PARTIAL:
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.UNVERIFIED

        if claim_key in _METADATA_CLAIMS:
            if warning_categories & _METADATA_UNDERMINING_WARNINGS:
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.VERIFIED

        if claim_key in _WORKING_TREE_CLAIMS:
            truncated = any(item.truncated for item in snapshot.overflow)
            if snapshot.completeness is SnapshotCompleteness.COMPLETE and not (
                truncated or warning_categories & _WORKING_TREE_UNDERMINING_WARNINGS
            ):
                return VerificationState.VERIFIED
            if snapshot.completeness in (
                SnapshotCompleteness.COMPLETE,
                SnapshotCompleteness.PARTIAL,
            ):
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.UNVERIFIED

        # snapshot_completeness: a direct self-describing observation.
        return VerificationState.VERIFIED

    # ------------------------------------------------------------------ #
    # Ordering and bounds
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ordered_evidence(
        records: Iterable[EvidenceRecord], anchors: dict[str, str]
    ) -> list[EvidenceRecord]:
        anchor_ids = set(anchors.values())

        def key(record: EvidenceRecord) -> tuple[int, str, str, str, str]:
            return (
                0 if record.evidence_id in anchor_ids else 1,
                record.evidence_type.value,
                record.reference.reference_kind.value,
                record.reference.value,
                record.evidence_id,
            )

        return sorted(records, key=key)

    @staticmethod
    def _ordered_candidates(records: Iterable[MemoryRecord]) -> list[MemoryRecord]:
        priority = {name: index for index, name in enumerate(_CANDIDATE_PRIORITY)}

        def key(record: MemoryRecord) -> tuple[int, str, str]:
            return (
                priority.get(record.claim.predicate, len(_CANDIDATE_PRIORITY)),
                record.claim.predicate,
                record.record_id,
            )

        return sorted(records, key=key)

    @staticmethod
    def _bounded(
        items: list,
        limit: int,
        kind: ProjectionOverflowKind,
        cutoff: str,
    ) -> tuple[list, ProjectionOverflow | None]:
        if len(items) <= limit:
            return items, None
        retained = items[:limit]
        return retained, ProjectionOverflow(
            overflow_id=f"overflow-{kind.value.replace('_', '-')}",
            kind=kind,
            configured_limit=limit,
            observed_count=len(items),
            retained_count=len(retained),
            omitted_count=len(items) - len(retained),
            deterministic_cutoff=cutoff,
        )

    @staticmethod
    def _result_completeness(
        snapshot: RepositorySnapshot,
        drift: RepositoryDriftAnalysis | None,
        overflow: Sequence[ProjectionOverflow],
    ) -> SnapshotCompleteness:
        worst = snapshot.completeness
        if drift is not None and (
            _COMPLETENESS_RANK[drift.completeness] > _COMPLETENESS_RANK[worst]
        ):
            worst = drift.completeness
        if overflow and worst is SnapshotCompleteness.COMPLETE:
            worst = SnapshotCompleteness.PARTIAL
        return worst


def project_repository_evidence(
    request: RepositoryEvidenceProjectionRequest,
) -> RepositoryEvidenceProjectionResult:
    """Module-level convenience over :class:`RepositoryEvidenceProjectionService`."""
    return RepositoryEvidenceProjectionService().project(request)
