"""Phase 40F — memory-migration export parser (the only byte-reading component).

Phase 40F is the first memory-migration phase permitted to read user-controlled
artifact bytes, and this module is the **only** place that does. It is the trust
boundary's other half: Phase 40E decided *whether* a declaration may be parsed;
this module, holding a matching ``ready_for_parsing`` assessment, actually reads
the declared bytes, proves they match what the user declared, interprets the
supported formats, and hands bounded parsed items to the pure projector.

The load-bearing rules, each enforced structurally below:

* **Nothing is opened before authorization.** :func:`parse_and_project` calls
  ``assessment.permits_parsing(bundle_fingerprint=bundle.fingerprint())`` — the
  exact Phase 40E gate, reused rather than re-implemented — before it touches a
  byte source. A rejected or stale assessment reads zero bytes and produces zero
  candidates. There is no second, weaker readiness check anywhere in this module.

* **Bytes are proven before they are trusted.** For every artifact the parser
  measures the actual bytes, compares their size to the declared size, recomputes
  the declared (accepted) digest, and compares it to the declaration. A size or
  digest mismatch produces a typed diagnostic and **no candidates** for that
  artifact. The Phase 40E ``DeclaredArtifactDigest.verified`` flag is never
  mutated; a confirmed integrity result is recorded in the separate Phase 40F
  :class:`~app.models.memory_migration_projection.VerifiedArtifactIntegrity`
  shape. Integrity means *these bytes are the declared bytes* — never that the
  statements inside them are true.

* **Archives are read defensively and never extracted to disk.** A
  ``chatgpt_export_archive`` is opened in memory from its verified bytes; members
  are bounded and screened for traversal, absolute paths, control characters,
  encryption, symlinks and device/socket/FIFO entries, and decompression-bomb
  shapes; only the single intended ``conversations.json`` member is read, and only
  through a bounded stream. Nothing is extracted, executed, or followed.

* **Parsing establishes interpretation, never authority.** No parsed item is a
  fact, a decision, a phase state, or a verified claim. The parser conservatively
  extracts user-visible ``user``/``assistant`` conversational text and
  user-authored documents; system, tool, and developer material is skipped with a
  typed, counted diagnostic and never becomes a candidate. Malformed or incomplete
  records are skipped with bounded diagnostics rather than repaired or fabricated.

* **Determinism is a promise.** Conversations are read in export order; messages
  are ordered by a stable traversal of the mapping tree (never JSON object
  insertion order); parsed items carry an explicit deterministic sequence index.
  Identical bytes always yield identical parsed items, and therefore identical
  candidates in identical order.

This module imports the archive/JSON/filesystem facilities it needs; the pure
projector it calls (:mod:`app.services.memory_migration_projection`) imports none
of them, which is what keeps the parse/project separation real.
"""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.models.memory_migration import (
    MemoryMigrationBundle,
    MigrationArtifactDescriptor,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationDigestAlgorithm,
)
from app.models.memory_migration_assessment import MemoryMigrationIntakeAssessment
from app.models.memory_migration_projection import (
    MAX_MIGRATION_CANDIDATES,
    MAX_MIGRATION_PROJECTION_DIAGNOSTICS,
    MAX_PARSED_ITEM_CHARS,
    MemoryMigrationCandidate,
    MemoryMigrationProjectionResult,
    MigrationCandidateRole,
    MigrationProjectionDiagnostic,
    MigrationProjectionDiagnosticCode,
    MIGRATION_PROJECTION_SEVERITY,
    MigrationProjectionSeverity,
    ParsedMigrationItem,
    CuratedMigrationBundleDocument,
    VerifiedArtifactIntegrity,
)
from app.services.memory_migration_intake import MAX_DECLARED_ARTIFACT_BYTES
from app.services.memory_migration_projection import (
    CandidateProjectionContext,
    project_artifact_items,
)

# --------------------------------------------------------------------------- #
# Archive-handling bounds.
#
# All are *uncompressed*-oriented, because the risk an archive poses is expansion:
# a small compressed payload that inflates to exhaust memory or disk. They are set
# well above any realistic ChatGPT export while still being a hard ceiling.
#
# The compression-ratio guard only applies above ``_MIN_RATIO_CHECK_BYTES`` so a
# tiny, highly-compressible-but-harmless member (an empty file, a short repeated
# string) is not mistaken for a bomb.
# --------------------------------------------------------------------------- #
MAX_ARCHIVE_MEMBERS = 8192
MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES = 1 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBER_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_COMPRESSION_RATIO = 200
_MIN_RATIO_CHECK_BYTES = 4096

_CONVERSATIONS_MEMBER_NAME = "conversations.json"

# The (format, container) pairs Phase 40F can actually parse. Every artifact in a
# ``ready_for_parsing`` bundle already passed the Phase 40E format/container
# checks, but this table is the parser's own explicit, fail-closed dispatch: a
# pair not listed here yields a typed diagnostic and reads nothing, so a future
# format addition can never arrive as silently-accepted generic text.
_FORMAT_CONTAINERS: dict[MigrationArtifactFormat, frozenset[MigrationContainerKind]] = {
    MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE: frozenset(
        {MigrationContainerKind.ZIP_ARCHIVE}
    ),
    MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON: frozenset(
        {MigrationContainerKind.SINGLE_FILE}
    ),
    MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT: frozenset(
        {MigrationContainerKind.SINGLE_FILE}
    ),
    MigrationArtifactFormat.CURATED_MARKDOWN_BUNDLE: frozenset(
        {MigrationContainerKind.SINGLE_FILE}
    ),
    MigrationArtifactFormat.CURATED_JSON_BUNDLE: frozenset(
        {MigrationContainerKind.SINGLE_FILE}
    ),
}

# ChatGPT author roles whose visible text may become a candidate. Everything else
# — ``system``, ``tool``, ``developer``, and any unrecognized role — is skipped
# with a counted diagnostic and never imported.
_CANDIDATE_MESSAGE_ROLES: dict[str, MigrationCandidateRole] = {
    "user": MigrationCandidateRole.USER,
    "assistant": MigrationCandidateRole.ASSISTANT,
}

_DIGEST_FUNCS = {
    MigrationDigestAlgorithm.SHA256: hashlib.sha256,
    MigrationDigestAlgorithm.SHA512: hashlib.sha512,
    MigrationDigestAlgorithm.SHA1: hashlib.sha1,
    MigrationDigestAlgorithm.MD5: hashlib.md5,
}


# =========================================================================== #
# Byte sources
# =========================================================================== #
class MigrationArtifactSourceError(Exception):
    """A declared artifact's bytes could not be obtained.

    Raised by a byte source rather than returning ``None`` so the orchestrator can
    distinguish "no bytes" from an empty artifact, and so the failure is reported
    as a typed ``artifact_source_missing`` diagnostic instead of crashing the run.
    """


class MigrationArtifactByteSource(ABC):
    """Resolves the actual bytes for one declared artifact.

    The single abstraction through which the parser obtains bytes. Isolating byte
    acquisition behind it keeps *all* Phase 40F I/O on the parser/input side and
    lets the orchestrator prove — by never calling it until authorization passes —
    that no byte is read before the Phase 40E gate.
    """

    @abstractmethod
    def read_artifact(self, artifact: MigrationArtifactDescriptor) -> bytes:
        """Return the artifact's bytes, or raise :class:`MigrationArtifactSourceError`."""


class InMemoryArtifactByteSource(MigrationArtifactByteSource):
    """A byte source backed by an in-memory ``artifact_id -> bytes`` mapping.

    The source callers use when they already hold the bytes (and the source the
    tests use), so parsing never requires a real filesystem. It performs no I/O at
    all, which is why archive-safety tests can drive real ZIP bytes through the
    parser without ever writing to disk.
    """

    def __init__(self, artifacts: Mapping[str, bytes]) -> None:
        self._data = dict(artifacts)

    def read_artifact(self, artifact: MigrationArtifactDescriptor) -> bytes:
        try:
            return self._data[artifact.artifact_id]
        except KeyError as exc:
            raise MigrationArtifactSourceError(
                "no bytes provided for the requested artifact"
            ) from exc


class FilesystemArtifactByteSource(MigrationArtifactByteSource):
    """A byte source that reads a declared relative path under a fixed root.

    The only Phase 40F component that performs real filesystem reads. It re-checks
    the declared path defensively even though Phase 40E already screened it (an
    absolute path, a ``..`` segment, or a resolved target escaping the root is
    refused here too — defense in depth at the point bytes are actually read), and
    it reads at most a bounded number of bytes so a mis-declared enormous file
    cannot exhaust memory. It never follows a symlink out of the root: the resolved
    target must remain inside it.
    """

    def __init__(
        self,
        root: Path,
        *,
        max_bytes: int = MAX_DECLARED_ARTIFACT_BYTES,
    ) -> None:
        self._root = Path(root).resolve()
        self._max_bytes = max_bytes

    def read_artifact(self, artifact: MigrationArtifactDescriptor) -> bytes:
        relative = artifact.declared_relative_path
        normalized = relative.replace("\\", "/")
        if (
            normalized.startswith("/")
            or (len(normalized) >= 2 and normalized[1] == ":")
            or ".." in normalized.split("/")
        ):
            raise MigrationArtifactSourceError("declared path is not a safe relative path")
        target = (self._root / normalized).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as exc:
            raise MigrationArtifactSourceError(
                "declared path resolves outside the bundle root"
            ) from exc
        if not target.is_file():
            raise MigrationArtifactSourceError("declared artifact is not a readable file")
        try:
            with open(target, "rb") as handle:
                data = handle.read(self._max_bytes + 1)
        except OSError as exc:
            raise MigrationArtifactSourceError("declared artifact could not be read") from exc
        if len(data) > self._max_bytes:
            raise MigrationArtifactSourceError("declared artifact exceeds the byte bound")
        return data


# =========================================================================== #
# Diagnostic helper
# =========================================================================== #
def _diagnostic(
    code: MigrationProjectionDiagnosticCode,
    message: str,
    *,
    subject_id: str | None = None,
    artifact_id: str | None = None,
    count: int | None = None,
) -> MigrationProjectionDiagnostic:
    return MigrationProjectionDiagnostic(
        code=code,
        message=message,
        subject_id=subject_id,
        artifact_id=artifact_id,
        count=count,
    )


# =========================================================================== #
# Parsed-artifact bundle (internal)
# =========================================================================== #
class _ArtifactParse:
    """The outcome of reading and parsing one artifact's bytes.

    A tiny internal carrier (not a wire shape) so the orchestrator can keep the
    verified integrity record, the parsed items, the diagnostics, and whether any
    byte was actually read in one return value.
    """

    __slots__ = ("integrity", "items", "diagnostics", "read")

    def __init__(
        self,
        *,
        integrity: VerifiedArtifactIntegrity | None = None,
        items: list[ParsedMigrationItem] | None = None,
        diagnostics: list[MigrationProjectionDiagnostic] | None = None,
        read: bool = False,
    ) -> None:
        self.integrity = integrity
        self.items = items or []
        self.diagnostics = diagnostics or []
        self.read = read


# =========================================================================== #
# Integrity verification
# =========================================================================== #
def _compute_digest(algorithm: MigrationDigestAlgorithm, data: bytes) -> str | None:
    factory = _DIGEST_FUNCS.get(algorithm)
    if factory is None:
        return None
    try:
        return factory(data).hexdigest()
    except ValueError:
        # A FIPS-enforcing build may refuse a weak algorithm. An accepted
        # (sha256/sha512) algorithm is always available, so this only guards the
        # defensive weak-algorithm path.
        return None


def _verify_integrity(
    artifact: MigrationArtifactDescriptor, data: bytes
) -> tuple[VerifiedArtifactIntegrity | None, list[MigrationProjectionDiagnostic]]:
    """Prove the read bytes match the declaration, or fail closed with a diagnostic."""

    observed_size = len(data)
    declared_size = artifact.declared_byte_size
    if declared_size is not None and declared_size != observed_size:
        return None, [
            _diagnostic(
                MigrationProjectionDiagnosticCode.ACTUAL_SIZE_MISMATCH,
                "actual artifact byte size does not match the declared size; the "
                "artifact is not the declared material and yields no candidates",
                artifact_id=artifact.artifact_id,
                count=observed_size,
            )
        ]

    digest = artifact.declared_digest
    if digest is None:
        # A ready bundle guarantees a declared digest; this is defensive.
        return None, [
            _diagnostic(
                MigrationProjectionDiagnosticCode.DIGEST_MISMATCH,
                "artifact declares no digest, so read bytes cannot be proven to be "
                "the declared material",
                artifact_id=artifact.artifact_id,
            )
        ]

    observed_digest = _compute_digest(digest.algorithm, data)
    if observed_digest is None or observed_digest != digest.value:
        return None, [
            _diagnostic(
                MigrationProjectionDiagnosticCode.DIGEST_MISMATCH,
                "recomputed artifact digest does not match the declared digest; the "
                "bytes are not the declared material and yield no candidates",
                artifact_id=artifact.artifact_id,
            )
        ]

    integrity = VerifiedArtifactIntegrity(
        artifact_id=artifact.artifact_id,
        artifact_fingerprint=artifact.fingerprint(),
        algorithm=digest.algorithm,
        declared_digest_value=digest.value,
        observed_digest_value=observed_digest,
        declared_byte_size=declared_size,
        observed_byte_size=observed_size,
    )
    return integrity, []


# =========================================================================== #
# Text / JSON helpers
# =========================================================================== #
def _decode_utf8(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _cap_text(text: str) -> tuple[str, int]:
    """Return content bounded to the parser item ceiling plus its original length."""

    return text[:MAX_PARSED_ITEM_CHARS], len(text)


def _timestamp_from_epoch(value: Any) -> datetime | None:
    """Convert a ChatGPT numeric ``create_time`` to a UTC datetime, deterministically.

    ``datetime.fromtimestamp`` with an explicit ``timezone.utc`` reads no clock; it
    is a pure conversion. A non-numeric, boolean, non-finite, or out-of-range value
    yields ``None`` rather than a fabricated time.
    """

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


# =========================================================================== #
# ChatGPT conversation parsing
# =========================================================================== #
def _conversation_identifier(conversation: dict[str, Any]) -> str | None:
    for key in ("conversation_id", "id"):
        value = conversation.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _ordered_message_nodes(
    mapping: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(node_id, node)`` pairs in a stable, insertion-order-independent order.

    Explicit roots (nodes whose parent is ``None``) are visited first, then only
    parent-consistent child edges, each level ordered by
    ``(message create_time, node_id)``. A missing parent is not promoted to a root,
    and a child reference cannot override the child's own parent declaration, so
    malformed input cannot manufacture ancestry. A ``visited`` set makes the
    traversal safe against a hostile cyclic mapping. The order does not depend on
    the order the mapping dict happened to enumerate, satisfying the determinism
    guarantee for semantically-equivalent inputs.
    """

    def sort_key(node_id: str) -> tuple[float, str]:
        node = mapping.get(node_id)
        message = node.get("message") if isinstance(node, dict) else None
        create_time = message.get("create_time") if isinstance(message, dict) else None
        if isinstance(create_time, (int, float)) and not isinstance(create_time, bool):
            return (float(create_time), node_id)
        return (float("inf"), node_id)

    roots = [
        node_id
        for node_id, node in mapping.items()
        if isinstance(node, dict) and node.get("parent") is None
    ]
    # Reverse-sorted onto a stack so popping yields ascending order.
    stack = sorted(roots, key=sort_key, reverse=True)
    visited: set[str] = set()
    ordered: list[tuple[str, dict[str, Any]]] = []
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        node = mapping[node_id]
        ordered.append((node_id, node))
        children = [
            child
            for child in (node.get("children") or [])
            if isinstance(child, str)
            and isinstance(mapping.get(child), dict)
            and mapping[child].get("parent") == node_id
        ]
        for child in sorted(children, key=sort_key, reverse=True):
            stack.append(child)
    return ordered


def _extract_message_text(content: Any) -> tuple[str | None, bool]:
    """Extract joined text from a ChatGPT message ``content`` object.

    Returns ``(text, is_text_content)``. ``is_text_content`` is ``False`` when the
    content is not a ``text`` payload (an image, audio, or tool result), so the
    caller can record a ``non_text_content_skipped`` finding rather than treating a
    non-text part as empty text.
    """

    if not isinstance(content, dict):
        return None, False
    if content.get("content_type") != "text":
        return None, False
    parts = content.get("parts")
    if not isinstance(parts, list):
        return None, True
    string_parts = [part for part in parts if isinstance(part, str)]
    if not string_parts:
        return None, True
    return "\n\n".join(string_parts), True


class _SkipCounts:
    """Accumulated per-artifact skip counts, so diagnostics stay bounded.

    A conversation export can contain thousands of system/tool messages; emitting
    one diagnostic each would blow the bounded diagnostic list and drown real
    findings. Instead each category is counted once per artifact and reported as a
    single diagnostic carrying the count.
    """

    __slots__ = (
        "malformed_conversations",
        "malformed_messages",
        "unsupported_roles",
        "non_text",
        "empty",
    )

    def __init__(self) -> None:
        self.malformed_conversations = 0
        self.malformed_messages = 0
        self.unsupported_roles = 0
        self.non_text = 0
        self.empty = 0

    def diagnostics(
        self, artifact: MigrationArtifactDescriptor
    ) -> list[MigrationProjectionDiagnostic]:
        results: list[MigrationProjectionDiagnostic] = []
        for count, code, message in (
            (
                self.malformed_conversations,
                MigrationProjectionDiagnosticCode.MALFORMED_CONVERSATION,
                "conversation records were skipped because they were not well-formed "
                "objects with a usable identifier and mapping",
            ),
            (
                self.malformed_messages,
                MigrationProjectionDiagnosticCode.MALFORMED_MESSAGE,
                "message records were skipped because they lacked a well-formed author "
                "or content structure",
            ),
            (
                self.unsupported_roles,
                MigrationProjectionDiagnosticCode.UNSUPPORTED_MESSAGE_ROLE,
                "messages were skipped because their author role is not user-visible "
                "conversational content (system, tool, or developer material)",
            ),
            (
                self.non_text,
                MigrationProjectionDiagnosticCode.NON_TEXT_CONTENT_SKIPPED,
                "messages were skipped because their content is not text",
            ),
            (
                self.empty,
                MigrationProjectionDiagnosticCode.EMPTY_CONTENT_SKIPPED,
                "messages were skipped because their text content was empty",
            ),
        ):
            if count:
                results.append(
                    _diagnostic(
                        code,
                        message,
                        artifact_id=artifact.artifact_id,
                        count=count,
                    )
                )
        return results


def _parse_conversations_bytes(
    artifact: MigrationArtifactDescriptor, data: bytes
) -> tuple[list[ParsedMigrationItem], list[MigrationProjectionDiagnostic]]:
    """Parse a ChatGPT ``conversations.json`` payload into bounded parsed items."""

    text = _decode_utf8(data)
    if text is None:
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.DECODE_ERROR,
                "conversations payload is not valid UTF-8",
                artifact_id=artifact.artifact_id,
            )
        ]
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.MALFORMED_JSON,
                "conversations payload is not parseable JSON",
                artifact_id=artifact.artifact_id,
            )
        ]

    if not isinstance(document, list):
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE,
                "conversations payload is not the expected list of conversations",
                artifact_id=artifact.artifact_id,
            )
        ]

    items: list[ParsedMigrationItem] = []
    counts = _SkipCounts()
    artifact_fingerprint = artifact.fingerprint()
    sequence = 0

    for conversation in document:
        if not isinstance(conversation, dict):
            counts.malformed_conversations += 1
            continue
        conversation_id = _conversation_identifier(conversation)
        mapping = conversation.get("mapping")
        if conversation_id is None or not isinstance(mapping, dict):
            counts.malformed_conversations += 1
            continue

        ordered_nodes = _ordered_message_nodes(mapping)
        reached_node_ids = {node_id for node_id, _node in ordered_nodes}
        counts.malformed_messages += sum(
            1
            for node_id, node in mapping.items()
            if node_id not in reached_node_ids
            and isinstance(node, dict)
            and node.get("message") is not None
        )

        for node_id, node in ordered_nodes:
            message = node.get("message")
            if message is None:
                # Root/placeholder nodes carry no message; skipping is normal and
                # not an error.
                continue
            if not isinstance(message, dict):
                counts.malformed_messages += 1
                continue
            author = message.get("author")
            role_name = author.get("role") if isinstance(author, dict) else None
            if not isinstance(role_name, str):
                counts.malformed_messages += 1
                continue
            role = _CANDIDATE_MESSAGE_ROLES.get(role_name)
            if role is None:
                counts.unsupported_roles += 1
                continue
            extracted, is_text = _extract_message_text(message.get("content"))
            if not is_text:
                counts.non_text += 1
                continue
            if extracted is None or not extracted.strip():
                counts.empty += 1
                continue

            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id.strip():
                message_id = node_id
            content, original_length = _cap_text(extracted)
            items.append(
                ParsedMigrationItem(
                    artifact_id=artifact.artifact_id,
                    artifact_fingerprint=artifact_fingerprint,
                    source_local_id=f"{conversation_id}:{message_id}",
                    source_container_id=conversation_id,
                    source_entry_id=message_id,
                    role=role,
                    source_sequence_index=sequence,
                    content=content,
                    original_content_length=original_length,
                    declared_source_timestamp=_timestamp_from_epoch(
                        message.get("create_time")
                    ),
                )
            )
            sequence += 1

    return items, counts.diagnostics(artifact)


# =========================================================================== #
# Archive parsing
# =========================================================================== #
def _member_basename(name: str) -> str:
    return name.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _is_unsafe_member_name(name: str) -> bool:
    if not name:
        return True
    normalized = name.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    if len(normalized) >= 2 and normalized[1] == ":":
        return True
    segments = normalized.split("/")
    if ".." in segments:
        return True
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in name):
        return True
    return False


def _is_special_member(info: zipfile.ZipInfo) -> bool:
    """Whether a member is a symlink or a device/socket/FIFO (never readable content)."""

    mode = (info.external_attr >> 16) & 0xFFFF
    if mode == 0:
        return False
    return (
        stat.S_ISLNK(mode)
        or stat.S_ISBLK(mode)
        or stat.S_ISCHR(mode)
        or stat.S_ISFIFO(mode)
        or stat.S_ISSOCK(mode)
    )


def _member_safety_violation(
    info: zipfile.ZipInfo,
) -> tuple[MigrationProjectionDiagnosticCode, str] | None:
    """Screen one archive member for a structural safety or per-member bound breach.

    A pure function of the member's metadata, extracted so the safety policy can be
    unit-tested against crafted members (an encrypted flag, a symlink mode, a
    traversing name) that stdlib ``zipfile`` cannot easily be made to *write*. It
    returns the ``(code, message)`` for the first violation, or ``None`` for a safe
    member. The running total-size bound is enforced by the caller because it
    depends on order.
    """

    if _is_unsafe_member_name(info.filename):
        return (
            MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
            "archive member path is absolute, traversing, or contains control "
            "characters",
        )
    if info.flag_bits & 0x1:
        return (
            MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
            "archive contains an encrypted member, which cannot be safely processed",
        )
    if _is_special_member(info):
        return (
            MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
            "archive contains a symlink or device-style member, which is not "
            "readable content",
        )
    if info.is_dir():
        return None
    if info.file_size > MAX_ARCHIVE_MEMBER_UNCOMPRESSED_BYTES:
        return (
            MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED,
            "archive member exceeds the per-member uncompressed bound",
        )
    if (
        info.file_size >= _MIN_RATIO_CHECK_BYTES
        and info.compress_size > 0
        and info.file_size / info.compress_size > MAX_ARCHIVE_COMPRESSION_RATIO
    ):
        return (
            MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED,
            "archive member has a decompression ratio beyond the safe bound",
        )
    return None


def _parse_chatgpt_archive(
    artifact: MigrationArtifactDescriptor, data: bytes
) -> tuple[list[ParsedMigrationItem], list[MigrationProjectionDiagnostic]]:
    """Read the conversations member from a verified ChatGPT export archive.

    Defensive throughout: the archive is opened in memory, every member is bounded
    and screened, only the intended ``conversations.json`` is read, and any safety
    violation fails the whole artifact closed with a typed diagnostic. Nothing is
    ever extracted to disk.
    """

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
                "artifact is declared a zip archive but is not a valid archive",
                artifact_id=artifact.artifact_id,
            )
        ]

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_MEMBERS:
            return [], [
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED,
                    "archive declares more members than the intake bound permits",
                    artifact_id=artifact.artifact_id,
                    count=len(infos),
                )
            ]

        total_uncompressed = 0
        safe_files: list[zipfile.ZipInfo] = []
        for info in infos:
            violation = _member_safety_violation(info)
            if violation is not None:
                code, message = violation
                return [], [
                    _diagnostic(code, message, artifact_id=artifact.artifact_id)
                ]
            if info.is_dir():
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES:
                return [], [
                    _diagnostic(
                        MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED,
                        "archive total uncompressed size exceeds the intake bound",
                        artifact_id=artifact.artifact_id,
                    )
                ]
            safe_files.append(info)

        candidates = [
            info
            for info in safe_files
            if _member_basename(info.filename) == _CONVERSATIONS_MEMBER_NAME
        ]
        if not candidates:
            return [], [
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARCHIVE_MEMBER_MISSING,
                    "archive contains no conversations.json member to parse",
                    artifact_id=artifact.artifact_id,
                )
            ]
        if len(candidates) != 1:
            return [], [
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
                    "archive contains multiple conversations.json members, so the "
                    "intended migration content is ambiguous",
                    artifact_id=artifact.artifact_id,
                    count=len(candidates),
                )
            ]
        target = sorted(candidates, key=lambda info: info.filename)[0]

        try:
            with archive.open(target) as handle:
                member_bytes = handle.read(MAX_ARCHIVE_MEMBER_UNCOMPRESSED_BYTES + 1)
        except (zipfile.BadZipFile, OSError, RuntimeError):
            return [], [
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION,
                    "archive conversations member could not be read safely",
                    artifact_id=artifact.artifact_id,
                )
            ]
        if len(member_bytes) > MAX_ARCHIVE_MEMBER_UNCOMPRESSED_BYTES:
            return [], [
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED,
                    "archive conversations member exceeds the per-member uncompressed "
                    "bound when read",
                    artifact_id=artifact.artifact_id,
                )
            ]

    return _parse_conversations_bytes(artifact, member_bytes)


# =========================================================================== #
# Curated / plain-text parsing
# =========================================================================== #
def _parse_plain_text(
    artifact: MigrationArtifactDescriptor,
    data: bytes,
    role: MigrationCandidateRole,
) -> tuple[list[ParsedMigrationItem], list[MigrationProjectionDiagnostic]]:
    text = _decode_utf8(data)
    if text is None:
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.DECODE_ERROR,
                "document is not valid UTF-8",
                artifact_id=artifact.artifact_id,
            )
        ]
    if not text.strip():
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.EMPTY_CONTENT_SKIPPED,
                "document has no non-whitespace content",
                artifact_id=artifact.artifact_id,
                count=1,
            )
        ]
    content, original_length = _cap_text(text)
    item = ParsedMigrationItem(
        artifact_id=artifact.artifact_id,
        artifact_fingerprint=artifact.fingerprint(),
        source_local_id=artifact.artifact_id,
        role=role,
        source_sequence_index=0,
        content=content,
        original_content_length=original_length,
    )
    return [item], []


def _parse_curated_json(
    artifact: MigrationArtifactDescriptor, data: bytes
) -> tuple[list[ParsedMigrationItem], list[MigrationProjectionDiagnostic]]:
    text = _decode_utf8(data)
    if text is None:
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.DECODE_ERROR,
                "curated bundle is not valid UTF-8",
                artifact_id=artifact.artifact_id,
            )
        ]
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.MALFORMED_JSON,
                "curated bundle is not parseable JSON",
                artifact_id=artifact.artifact_id,
            )
        ]
    if not isinstance(payload, dict):
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE,
                "curated bundle is not the expected object shape",
                artifact_id=artifact.artifact_id,
            )
        ]
    try:
        document = CuratedMigrationBundleDocument(**payload)
    except Exception:
        # A curated bundle that fails the versioned, extra="forbid" contract is
        # reported as an unsupported shape without echoing any field it carried.
        return [], [
            _diagnostic(
                MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE,
                "curated bundle does not satisfy the versioned curated contract",
                artifact_id=artifact.artifact_id,
            )
        ]

    items: list[ParsedMigrationItem] = []
    artifact_fingerprint = artifact.fingerprint()
    for sequence, entry in enumerate(document.entries):
        content, original_length = _cap_text(entry.text)
        items.append(
            ParsedMigrationItem(
                artifact_id=artifact.artifact_id,
                artifact_fingerprint=artifact_fingerprint,
                source_local_id=entry.entry_id,
                source_entry_id=entry.entry_id,
                role=entry.role,
                source_sequence_index=sequence,
                content=content,
                original_content_length=original_length,
                declared_source_timestamp=entry.timestamp,
            )
        )
    return items, []


# =========================================================================== #
# Per-artifact dispatch
# =========================================================================== #
def _unsupported_dispatch(
    artifact: MigrationArtifactDescriptor,
) -> MigrationProjectionDiagnostic | None:
    allowed = _FORMAT_CONTAINERS.get(artifact.artifact_format)
    if allowed is None:
        return _diagnostic(
            MigrationProjectionDiagnosticCode.UNSUPPORTED_FORMAT,
            "artifact format has no Phase 40F parser",
            artifact_id=artifact.artifact_id,
        )
    if artifact.container not in allowed:
        return _diagnostic(
            MigrationProjectionDiagnosticCode.UNSUPPORTED_CONTAINER,
            "artifact container is not supported for this format in Phase 40F",
            artifact_id=artifact.artifact_id,
        )
    return None


def _parse_artifact(
    artifact: MigrationArtifactDescriptor,
    source: MigrationArtifactByteSource,
) -> _ArtifactParse:
    """Read, verify, and parse one artifact. Byte access happens only here."""

    unsupported = _unsupported_dispatch(artifact)
    if unsupported is not None:
        return _ArtifactParse(diagnostics=[unsupported], read=False)

    try:
        data = source.read_artifact(artifact)
    except MigrationArtifactSourceError:
        return _ArtifactParse(
            diagnostics=[
                _diagnostic(
                    MigrationProjectionDiagnosticCode.ARTIFACT_SOURCE_MISSING,
                    "declared artifact bytes could not be obtained",
                    artifact_id=artifact.artifact_id,
                )
            ],
            read=False,
        )

    integrity, integrity_diags = _verify_integrity(artifact, data)
    if integrity is None:
        return _ArtifactParse(diagnostics=integrity_diags, read=True)

    fmt = artifact.artifact_format
    if fmt is MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE:
        items, parse_diags = _parse_chatgpt_archive(artifact, data)
    elif fmt is MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON:
        items, parse_diags = _parse_conversations_bytes(artifact, data)
    elif fmt is MigrationArtifactFormat.CURATED_JSON_BUNDLE:
        items, parse_diags = _parse_curated_json(artifact, data)
    else:
        # plain_text_document and curated_markdown_bundle: conservative document
        # text. Markdown is not semantically interpreted — treating it as text
        # avoids manufacturing structured facts from prose.
        items, parse_diags = _parse_plain_text(
            artifact, data, MigrationCandidateRole.DOCUMENT
        )

    return _ArtifactParse(
        integrity=integrity,
        items=items,
        diagnostics=parse_diags,
        read=True,
    )


# =========================================================================== #
# Result assembly
# =========================================================================== #
def _finalize_diagnostics(
    diagnostics: Sequence[MigrationProjectionDiagnostic],
    *,
    subject_id: str,
) -> list[MigrationProjectionDiagnostic]:
    """Deduplicate, canonically order, and bound the diagnostic list.

    Mirrors the Phase 40E finalize discipline: errors are retained ahead of
    ``info`` findings when truncating, so bounding the list can never hide the fact
    that something failed, and the truncation notice itself is an error.
    """

    ordered = sorted(diagnostics, key=lambda item: item.sort_key())
    deduplicated: list[MigrationProjectionDiagnostic] = []
    seen: set[tuple[str, str, str, str]] = set()
    for finding in ordered:
        key = finding.sort_key()
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(finding)

    if len(deduplicated) <= MAX_MIGRATION_PROJECTION_DIAGNOSTICS:
        return deduplicated

    by_severity = sorted(
        deduplicated,
        key=lambda item: (
            0
            if MIGRATION_PROJECTION_SEVERITY[item.code]
            is MigrationProjectionSeverity.ERROR
            else 1,
            item.sort_key(),
        ),
    )
    kept = by_severity[: MAX_MIGRATION_PROJECTION_DIAGNOSTICS - 1]
    kept.append(
        _diagnostic(
            MigrationProjectionDiagnosticCode.DIAGNOSTICS_TRUNCATED,
            "further findings were omitted to satisfy the diagnostic bound; the "
            "result is not fully described",
            subject_id=subject_id,
            count=len(deduplicated) - (MAX_MIGRATION_PROJECTION_DIAGNOSTICS - 1),
        )
    )
    return sorted(kept, key=lambda item: item.sort_key())


def _rejected_result(
    bundle: MemoryMigrationBundle,
    assessment: MemoryMigrationIntakeAssessment,
    bundle_fingerprint: str,
    diagnostic: MigrationProjectionDiagnostic,
) -> MemoryMigrationProjectionResult:
    return MemoryMigrationProjectionResult(
        bundle_id=bundle.bundle_id,
        bundle_fingerprint=bundle_fingerprint,
        assessment_bundle_fingerprint=assessment.bundle_fingerprint,
        gate_permitted=False,
        artifacts_read=0,
        integrity_results=[],
        candidates=[],
        diagnostics=[diagnostic],
    )


def parse_and_project(
    bundle: MemoryMigrationBundle,
    assessment: MemoryMigrationIntakeAssessment,
    source: MigrationArtifactByteSource,
) -> MemoryMigrationProjectionResult:
    """Parse a ready bundle's artifacts and project bounded candidates.

    The single Phase 40F entry point. It authorizes against the Phase 40E gate
    before touching ``source``, reads and integrity-verifies each artifact, parses
    the supported formats, projects candidates through the pure projector under a
    global candidate budget, and returns a deterministic, canonically-ordered
    result. It persists nothing and imports nothing.
    """

    bundle_fingerprint = bundle.fingerprint()

    # Authorization gate — reused Phase 40E contract, no second implementation.
    # No byte source is touched before this passes.
    if not assessment.ready_for_parsing:
        return _rejected_result(
            bundle,
            assessment,
            bundle_fingerprint,
            _diagnostic(
                MigrationProjectionDiagnosticCode.ASSESSMENT_GATE_REJECTED,
                "the intake assessment did not reach ready_for_parsing; no artifact "
                "byte may be read",
                subject_id=bundle.bundle_id,
            ),
        )
    if not assessment.permits_parsing(bundle_fingerprint=bundle_fingerprint):
        return _rejected_result(
            bundle,
            assessment,
            bundle_fingerprint,
            _diagnostic(
                MigrationProjectionDiagnosticCode.STALE_ASSESSMENT,
                "the assessment does not correspond to the current bundle "
                "declaration; a stale or mismatched assessment authorizes nothing",
                subject_id=bundle.bundle_id,
            ),
        )

    diagnostics: list[MigrationProjectionDiagnostic] = []
    integrity_results: list[VerifiedArtifactIntegrity] = []
    candidates: list[MemoryMigrationCandidate] = []
    artifacts_read = 0
    remaining_budget = MAX_MIGRATION_CANDIDATES
    total_omitted = 0

    provenance = bundle.provenance
    for artifact in bundle.normalized().artifacts:
        try:
            parsed = _parse_artifact(artifact, source)
        except Exception:
            # One artifact's unexpected failure must not crash the run or leak an
            # exception message. Fail closed for this artifact only.
            diagnostics.append(
                _diagnostic(
                    MigrationProjectionDiagnosticCode.PROJECTION_FAILURE,
                    "an unexpected error prevented parsing this artifact; it yields "
                    "no candidates",
                    artifact_id=artifact.artifact_id,
                )
            )
            continue

        if parsed.read:
            artifacts_read += 1
        diagnostics.extend(parsed.diagnostics)
        if parsed.integrity is not None:
            integrity_results.append(parsed.integrity)
        if not parsed.items:
            continue

        context = CandidateProjectionContext(
            bundle_id=bundle.bundle_id,
            bundle_fingerprint=bundle_fingerprint,
            source_artifact_format=artifact.artifact_format,
            source_container=artifact.container,
            observed_digest_algorithm=parsed.integrity.algorithm,
            observed_digest_value=parsed.integrity.observed_digest_value,
            custody=provenance.custody,
            source=provenance.source,
            target_scope=bundle.target_scope,
        )
        outcome = project_artifact_items(
            items=parsed.items,
            context=context,
            remaining_budget=remaining_budget,
        )
        candidates.extend(outcome.candidates)
        diagnostics.extend(outcome.diagnostics)
        remaining_budget -= outcome.produced
        total_omitted += outcome.omitted

    if total_omitted:
        diagnostics.append(
            _diagnostic(
                MigrationProjectionDiagnosticCode.CANDIDATE_COUNT_OVERFLOW,
                "the candidate budget was reached; further candidates were not "
                "created and are reported rather than silently dropped",
                subject_id=bundle.bundle_id,
                count=total_omitted,
            )
        )

    ordered_candidates = sorted(candidates, key=lambda item: item.sort_key())
    ordered_integrity = sorted(
        integrity_results, key=lambda item: item.artifact_id
    )
    ordered_diagnostics = _finalize_diagnostics(
        diagnostics, subject_id=bundle.bundle_id
    )

    return MemoryMigrationProjectionResult(
        bundle_id=bundle.bundle_id,
        bundle_fingerprint=bundle_fingerprint,
        assessment_bundle_fingerprint=assessment.bundle_fingerprint,
        gate_permitted=True,
        artifacts_read=artifacts_read,
        integrity_results=ordered_integrity,
        candidates=ordered_candidates,
        diagnostics=ordered_diagnostics,
    )
