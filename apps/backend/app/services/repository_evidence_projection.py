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

* **Timestamps** are caller-owned on two distinct axes.
  ``snapshot.observed_at`` is the repository observation time (and the
  ``captured_at`` of snapshot-derived evidence); ``drift.observed_at`` is the
  drift evidence capture time; ``request.recorded_at`` is the *recording*
  time and the deterministic ``created_at`` of every projected candidate. The
  service never substitutes one axis for another and never reads a clock.
  Awareness must be consistent (all naive or all aware), ``drift.observed_at``
  may not precede ``snapshot.observed_at`` when both are projected, and
  ``recorded_at`` may not precede the observation it records. Evidence
  ``captured_at`` prefers each observer item's own capture time; ``valid_until``
  is always ``None`` — no validity duration is invented. Naive datetimes are
  serialized as-is via ISO format for hashing; they are never normalized
  through the host-local timezone.
* **Identifiers** are content-derived via canonical JSON + SHA-256 (the
  drift service's private helper uses SHA-1, so it is deliberately not
  reused) over *all* output-driving data, so a different semantic output
  always yields a different id. The projection id folds in the project,
  repository, snapshot and optional drift identities, both observation times,
  the recording time, and the configured limits; a candidate id folds in the
  source snapshot id, the source drift id when applicable, the full claim
  (subject/predicate/value/value-kind), scope, source, both timestamps, the
  verification standing, and the sorted evidence ids. No UUIDs, no ``hash()``,
  no wall clock, no input-order dependence. A duplicate generated id raises
  :class:`ProjectionDuplicateIdError` instead of silently collapsing records.
* **Verification is claim-dependent, never automatic.** Git-derived evidence
  is not auto-trusted: ``verified`` requires a verified repository identity,
  a direct observation, and no warning/limitation/truncation undermining that
  specific claim family; partial snapshots, relevant observer warnings, and
  material limitations downgrade to ``partially_verified``; an unverified
  identity leaves every claim ``unverified``. A drift with ``complete``
  completeness but a material warning, limitation, or truncation is *not*
  automatically ``verified``. ``confidence`` is never set.
* **Candidates are projected inactive.** Every projected candidate uses
  ``LifecycleState.INACTIVE``: projection does not activate records. Active
  standing is reserved for later active-state selection under the existing
  Phase 37A/37B lifecycle contract, never asserted by projection.
* **Identity gating.** ``unsafe_location``, ``mismatched_root``, and
  ``mismatched_remote`` identity statuses block projection with a fatal
  domain error (untrustworthy scoping must not manufacture records). A
  drift analysis is required to describe the *same* repository as the
  snapshot across the stable identity fields (repository id, normalized and
  canonical roots, and primary remote identity when both are present), not by
  repository id alone; a mismatch is fatal and never echoes secret-bearing
  remote text. A detached HEAD is an observed ``operation_state`` value,
  never fatal.
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
    ObserverLimitationCategory,
    ObserverWarningCategory,
    RepositoryDriftAnalysis,
    RepositoryIdentity,
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
    repository across the stable identity fields. Never carries secret-bearing
    remote text."""


class ProjectionLimitError(RepositoryEvidenceProjectionError):
    """Raised for an impossible result configuration — for example a
    ``max_evidence_records`` too small to retain the evidence that the retained
    candidates reference (retaining candidates while dropping their support
    would produce dangling ``evidence_ids``)."""


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
    # Core repository identity/state.
    "identity_status",
    "current_commit",
    "current_branch",
    "working_tree_state",
    "operation_state",
    "snapshot_completeness",
    "upstream_reference",
    "default_branch",
    "drift_status",
    # Optional aggregates (drift baseline/totals, then working-tree and
    # change-kind counts). Retained only after the core state above.
    "drift_baseline_commit",
    "drifted_file_count",
    "staged_count",
    "unstaged_count",
    "untracked_count",
    "conflicted_count",
    "added_count",
    "modified_count",
    "deleted_count",
    "renamed_count",
    "copied_count",
    "type_changed_count",
    "unknown_count",
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
# Every drift-derived claim (status, baseline commit, and the change-kind and
# total aggregates) verifies under the same claim-relative drift policy.
_DRIFT_CLAIMS = frozenset(
    {
        "drift_status",
        "drift_baseline_commit",
        "drifted_file_count",
        "added_count",
        "modified_count",
        "deleted_count",
        "renamed_count",
        "copied_count",
        "type_changed_count",
        "unknown_count",
    }
)

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

# Warnings that undermine drift-derived claims: any completeness/coverage or
# metadata-integrity signal weakens what a drift analysis can attest.
_DRIFT_UNDERMINING_WARNINGS = (
    _METADATA_UNDERMINING_WARNINGS | _WORKING_TREE_UNDERMINING_WARNINGS
)

# Limitations that are *material* to trust — a real coverage/availability gap,
# not an inherent property of a deliberately metadata-only observer. A material
# limitation in the relevant family degrades verification the same way a warning
# does; the benign "…_not_included"/"metadata_only" limitations do not, because
# they describe the observer's fixed scope rather than a failure to observe.
_MATERIAL_LIMITATIONS = frozenset(
    {
        ObserverLimitationCategory.BOUNDED_COLLECTION,
        ObserverLimitationCategory.UNSUPPORTED_DATA,
        ObserverLimitationCategory.UNAVAILABLE_INFORMATION,
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


def _is_aware(value: datetime) -> bool:
    # A datetime is timezone-aware iff it carries a concrete UTC offset. Used to
    # reject mixed naive/aware inputs before any ordering comparison (comparing
    # a naive and an aware datetime raises, and would otherwise leak host-local
    # assumptions).
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


# --------------------------------------------------------------------------- #
# Remote reference safety (Phase 39A §7)
# --------------------------------------------------------------------------- #
def _remote_reference_is_safe(url: str) -> bool:
    """Return whether a remote URL is safe to project as an evidence reference.

    Deterministic and dependency-free. A safe reference must not carry
    credential material or extra request components: password/userinfo
    credentials, query parameters, fragments, or encoded credential-bearing
    authority all make it ineligible. An ambiguous remote is omitted
    conservatively (fail closed), but an ordinary SSH remote using the normal
    ``git@host`` username syntax is *not* treated as credential-bearing merely
    for that syntax — only a ``user:password`` userinfo is.
    """
    text = url.strip()
    if not text:
        return False
    lowered = text.lower()

    # Query and fragment components can smuggle tokens; reject either.
    if "?" in text or "#" in text:
        return False
    # Percent-encoded ``@`` or ``:`` can hide credential-bearing userinfo in the
    # authority; reject conservatively rather than decode.
    if "%40" in lowered or "%3a" in lowered:
        return False

    if "://" in text:
        scheme, rest = text.split("://", 1)
        authority = rest.split("/", 1)[0]
        if "@" in authority:
            userinfo = authority.split("@", 1)[0]
            if ":" in userinfo:
                # scheme://user:password@host — explicit credentials.
                return False
            # A bare username in the authority is normal only for SSH-family
            # schemes (ssh://git@host); over http(s) a bare userinfo is
            # typically a token, so omit it conservatively.
            return scheme.lower() in ("ssh", "git")
        return True

    # No scheme: scp-like SSH syntax ``[user@]host:path`` or a bare/local path.
    host_part = text.split(":", 1)[0]
    if "@" in host_part:
        userinfo = host_part.split("@", 1)[0]
        # ``git@host`` (bare username) is safe; ``user:password@host`` is not.
        return ":" not in userinfo
    return True


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
        recorded_at = request.recorded_at

        self._validate_contract_versions(snapshot, drift)
        self._validate_timestamps(snapshot, drift, recorded_at)
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

        # Limitations are not silently discarded: each is projected as a bounded
        # skipped-observation descriptor (never inlining secret-bearing text).
        skipped.extend(
            f"snapshot-limitation {item.limitation_id} ({item.category.value})"
            for item in snapshot.limitations
        )
        if drift is not None:
            skipped.extend(
                f"drift-limitation {item.limitation_id} ({item.category.value})"
                for item in drift.limitations
            )

        candidate_records = self._ordered_candidates(candidates_by_id.values())
        warnings = sorted(warnings)
        skipped = sorted(skipped)

        # Candidates are bounded first so evidence retention can honor exactly
        # which evidence the *retained* candidates reference; bounding evidence
        # before candidates could drop support a retained candidate still cites.
        candidate_records, candidate_overflow = self._bounded(
            candidate_records,
            limits.max_candidate_records,
            ProjectionOverflowKind.CANDIDATE_RECORD_COUNT,
            "documented candidate priority order (core state before aggregates)",
        )
        referenced_evidence_ids = {
            evidence_id
            for record in candidate_records
            for evidence_id in record.evidence_ids
        }
        evidence_records = self._ordered_evidence(evidence_by_id.values(), anchors)
        evidence_records, evidence_overflow = self._bounded_evidence(
            evidence_records,
            referenced_evidence_ids,
            limits.max_evidence_records,
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
                    "recorded_at": _canonical_datetime(recorded_at),
                    "drift_id": drift.drift_id if drift is not None else None,
                    "drift_observed_at": (
                        _canonical_datetime(drift.observed_at)
                        if drift is not None
                        else None
                    ),
                    # Configured limits change the retained/overflow output, so
                    # they are part of projection identity: different limits
                    # yield a different projection id.
                    "limits": {
                        "max_evidence_records": limits.max_evidence_records,
                        "max_candidate_records": limits.max_candidate_records,
                        "max_warnings": limits.max_warnings,
                        "max_skipped_observations": limits.max_skipped_observations,
                        "max_file_path_summary_items": (
                            limits.max_file_path_summary_items
                        ),
                    },
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
        snapshot: RepositorySnapshot,
        drift: RepositoryDriftAnalysis | None,
        recorded_at: datetime,
    ) -> None:
        # Guards models built via ``model_construct`` (validation bypassed):
        # without an observation timestamp there is no deterministic time base.
        if not isinstance(snapshot.observed_at, datetime):
            raise ProjectionTimestampError(
                "snapshot.observed_at is required; the projection has no clock"
            )
        if not isinstance(recorded_at, datetime):
            raise ProjectionTimestampError(
                "request.recorded_at is required; the projection has no clock"
            )
        if drift is not None and not isinstance(drift.observed_at, datetime):
            raise ProjectionTimestampError(
                "drift_analysis.observed_at is required; the projection has no clock"
            )

        # Awareness must be consistent across every projected timestamp: mixing
        # naive and aware datetimes is rejected rather than silently resolved
        # through a host-local assumption, and it also makes the ordering
        # comparisons below well-defined.
        observed_at = snapshot.observed_at
        stamps: list[tuple[str, datetime]] = [
            ("snapshot.observed_at", observed_at),
            ("request.recorded_at", recorded_at),
        ]
        if drift is not None:
            stamps.append(("drift_analysis.observed_at", drift.observed_at))
        if len({_is_aware(value) for _, value in stamps}) > 1:
            raise ProjectionTimestampError(
                "projected timestamps must share timezone awareness "
                "(all naive or all aware); no implicit local-time or UTC "
                "conversion is performed"
            )

        # Drift observation cannot precede the snapshot observation it is
        # projected alongside, and the recording time cannot precede either
        # observation it records.
        if drift is not None and drift.observed_at < observed_at:
            raise ProjectionTimestampError(
                "drift_analysis.observed_at must not precede snapshot.observed_at"
            )
        if recorded_at < observed_at:
            raise ProjectionTimestampError(
                "request.recorded_at must not precede snapshot.observed_at"
            )
        if drift is not None and recorded_at < drift.observed_at:
            raise ProjectionTimestampError(
                "request.recorded_at must not precede drift_analysis.observed_at"
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
            RepositoryEvidenceProjectionService._require_same_repository(
                identity, drift_identity
            )
            if drift_identity.status in _FATAL_IDENTITY_STATUSES:
                raise ProjectionIdentityError(
                    f"drift repository identity status {drift_identity.status.value!r} "
                    "prevents trustworthy scoping; refusing to project candidates"
                )

    @staticmethod
    def _require_same_repository(
        snapshot_identity: RepositoryIdentity, drift_identity: RepositoryIdentity
    ) -> None:
        """Require the drift analysis to describe the *same* repository as the
        snapshot across the stable identity fields, not by ``repository_id``
        alone (Phase 39A §6).

        The primary remote is compared only when both sides carry one; the raw
        remote value is never placed in the error message, because a remote URL
        can embed credentials and an exception must never leak secret text.
        """
        for field in ("repository_id", "normalized_root", "canonical_root"):
            if getattr(snapshot_identity, field) != getattr(drift_identity, field):
                raise ProjectionInputMismatchError(
                    "drift analysis does not match the snapshot repository "
                    f"(differing {field}); refusing to project across identities"
                )
        snapshot_remote = snapshot_identity.primary_remote_url
        drift_remote = drift_identity.primary_remote_url
        if (
            snapshot_remote is not None
            and drift_remote is not None
            and snapshot_remote != drift_remote
        ):
            raise ProjectionInputMismatchError(
                "drift analysis does not match the snapshot repository "
                "(differing primary remote identity); refusing to project "
                "across identities"
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
        elif not _remote_reference_is_safe(remote):
            # The remote is credential-bearing or otherwise ambiguous, so it is
            # omitted conservatively. The raw value is never echoed — a reference,
            # metadata field, skipped note, or exception must never carry secrets.
            skipped.append(
                "configured_remote: omitted (remote reference is credential-bearing "
                "or ambiguous)"
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
        recorded_at = request.recorded_at
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
            verification_state = self._claim_verification(claim_key, snapshot, drift)
            sorted_evidence_ids = sorted(evidence_ids)
            source_drift_id = None
            if extra_metadata is not None:
                source_drift_id = extra_metadata.get("source_drift_id")
            # Candidate identity folds in every output-driving field so that two
            # immutable records differing in any of them get distinct ids: the
            # full claim (subject/predicate/value/value-kind), scope, source, the
            # source snapshot id, the source drift id when the candidate is
            # drift-derived, both timestamps, the verification standing, and the
            # sorted evidence set.
            record_id = _stable_id(
                "candidate",
                {
                    "project_id": request.project_id,
                    "scope_type": scope.scope_type.value,
                    "scope_id": scope.scope_id,
                    "subject": repository_id,
                    "predicate": claim_key,
                    "value": value,
                    "value_kind": value_kind.value,
                    "source_id": source.source_id,
                    "source_snapshot_id": snapshot.snapshot_id,
                    "source_drift_id": source_drift_id,
                    "observed_at": _canonical_datetime(observed_at),
                    "recorded_at": _canonical_datetime(recorded_at),
                    "verification_state": verification_state.value,
                    "evidence_ids": sorted_evidence_ids,
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
                verification_state=verification_state,
                # Projection never activates records: candidates are inactive
                # until a later active-state selection promotes them under the
                # existing Phase 37A/37B lifecycle contract.
                lifecycle_state=LifecycleState.INACTIVE,
                confidence=None,
                evidence_ids=sorted_evidence_ids,
                observed_at=observed_at,
                created_at=recorded_at,
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
            drift_refs = snapshot_refs("drift")
            add(
                "drift_status",
                drift.drift_status.value,
                ClaimValueKind.ENUM,
                drift_refs,
                extra_metadata=drift_meta,
            )
            # Baseline commit is a direct drift datum; project it only when the
            # drift analysis actually resolved one (never a serialized ``None``).
            if drift.baseline_commit_hash is None:
                skipped.append(
                    "drift_baseline_commit: omitted (no baseline commit resolved)"
                )
            else:
                add(
                    "drift_baseline_commit",
                    drift.baseline_commit_hash,
                    ClaimValueKind.IDENTIFIER,
                    drift_refs,
                    extra_metadata=drift_meta,
                )
            # Bounded aggregate change-kind totals straight from the drift
            # summary the observer already computed — no per-file record is
            # created, so file-count growth cannot flood the projection.
            summary = drift.summary
            for claim_key, count in (
                ("drifted_file_count", summary.total_changed_files),
                ("added_count", summary.added_count),
                ("modified_count", summary.modified_count),
                ("deleted_count", summary.deleted_count),
                ("renamed_count", summary.renamed_count),
                ("copied_count", summary.copied_count),
                ("type_changed_count", summary.type_changed_count),
                ("unknown_count", summary.unknown_count),
            ):
                add(
                    claim_key,
                    str(count),
                    ClaimValueKind.INTEGER,
                    drift_refs,
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
        """Claim-dependent verification policy (Phase 39A §5/§7).

        Never automatic: ``verified`` requires a verified identity and no
        warning, material limitation, or truncation undermining the specific
        claim family. Trust degrades relative to the claim, so an unrelated
        warning about a different family never downgrades an unaffected claim.
        """
        if snapshot.repository_identity.status is not RepositoryIdentityStatus.VERIFIED:
            return VerificationState.UNVERIFIED

        warning_categories = {item.category for item in snapshot.warnings}
        snapshot_material_limitation = any(
            item.category in _MATERIAL_LIMITATIONS for item in snapshot.limitations
        )

        if claim_key in _DRIFT_CLAIMS:
            if drift is None:
                return VerificationState.UNVERIFIED
            # Complete-but-degraded is not automatically verified: a drift
            # warning, a material drift limitation, or drift truncation all
            # keep a complete drift analysis at partially_verified.
            drift_warning_categories = {item.category for item in drift.warnings}
            drift_truncated = any(item.truncated for item in drift.overflow)
            drift_material_limitation = any(
                item.category in _MATERIAL_LIMITATIONS for item in drift.limitations
            )
            drift_undermined = (
                bool(drift_warning_categories & _DRIFT_UNDERMINING_WARNINGS)
                or drift_truncated
                or drift_material_limitation
            )
            if (
                drift.completeness is SnapshotCompleteness.COMPLETE
                and not drift_undermined
            ):
                return VerificationState.VERIFIED
            if drift.completeness in (
                SnapshotCompleteness.COMPLETE,
                SnapshotCompleteness.PARTIAL,
            ):
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.UNVERIFIED

        if claim_key in _METADATA_CLAIMS:
            if (
                warning_categories & _METADATA_UNDERMINING_WARNINGS
                or snapshot_material_limitation
            ):
                return VerificationState.PARTIALLY_VERIFIED
            return VerificationState.VERIFIED

        if claim_key in _WORKING_TREE_CLAIMS:
            truncated = any(item.truncated for item in snapshot.overflow)
            if snapshot.completeness is SnapshotCompleteness.COMPLETE and not (
                truncated
                or warning_categories & _WORKING_TREE_UNDERMINING_WARNINGS
                or snapshot_material_limitation
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
    def _bounded_evidence(
        ordered_evidence: list[EvidenceRecord],
        referenced_ids: set[str],
        limit: int,
    ) -> tuple[list[EvidenceRecord], ProjectionOverflow | None]:
        """Bound evidence without ever dropping support a retained candidate
        cites (Phase 39A §1).

        Evidence referenced by a retained candidate is retained in full and
        prioritized ahead of unreferenced evidence. Only unreferenced evidence
        may overflow. If the configured limit cannot even hold the referenced
        evidence, that is an impossible result configuration — raising a focused
        :class:`ProjectionLimitError` rather than returning candidates whose
        ``evidence_ids`` dangle.
        """
        # Defensive: every referenced id must exist in the evidence pool. A
        # missing one is an internal construction fault, not a bound question.
        available_ids = {record.evidence_id for record in ordered_evidence}
        missing = referenced_ids - available_ids
        if missing:
            raise ProjectionLimitError(
                "retained candidates reference evidence that was never built "
                f"({len(missing)} missing id(s)); refusing to emit dangling "
                "evidence references"
            )

        required = [
            record for record in ordered_evidence
            if record.evidence_id in referenced_ids
        ]
        optional = [
            record for record in ordered_evidence
            if record.evidence_id not in referenced_ids
        ]
        if len(required) > limit:
            raise ProjectionLimitError(
                f"max_evidence_records={limit} is too small to retain the "
                f"{len(required)} evidence record(s) referenced by retained "
                "candidates; increase the limit or reduce retained candidates"
            )

        # Referenced evidence first (all kept), then unreferenced up to the
        # limit; only unreferenced evidence can be omitted.
        combined = required + optional
        if len(combined) <= limit:
            return combined, None
        retained = combined[:limit]
        return retained, ProjectionOverflow(
            overflow_id="overflow-evidence-record-count",
            kind=ProjectionOverflowKind.EVIDENCE_RECORD_COUNT,
            configured_limit=limit,
            observed_count=len(combined),
            retained_count=len(retained),
            omitted_count=len(combined) - len(retained),
            deterministic_cutoff=(
                "candidate-referenced evidence first (always retained), then "
                "unreferenced evidence by type/kind/value/id"
            ),
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
