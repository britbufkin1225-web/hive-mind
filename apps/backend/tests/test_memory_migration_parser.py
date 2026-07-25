"""Phase 40F — export parser and orchestration tests.

Covers the byte-reading half of Phase 40F: the reused Phase 40E authorization
gate (and proof that no byte is read before it passes), actual byte-integrity
verification, defensive archive handling, conservative ChatGPT export parsing,
curated/plain-text parsing, and the determinism and value-safety properties the
result promises.

Fixtures are synthetic throughout — no real user export or private conversation
archive appears here — and all bytes are driven through an in-memory source, so a
passing run touches no real filesystem and proves the pipeline rather than
assuming it.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.models.active_memory import (
    MemorySource,
    MemorySourceType,
    VerificationState,
)
from app.models.memory_migration import (
    DeclaredArtifactDigest,
    MemoryMigrationBundle,
    MigrationArtifactDescriptor,
    MigrationArtifactFormat,
    MigrationContainerKind,
    MigrationCustodyKind,
    MigrationDigestAlgorithm,
    MigrationEntryKind,
    MigrationProvenance,
)
from app.models.memory_migration_projection import (
    MigrationCandidateRole,
    MigrationProjectionDiagnosticCode,
)
from app.services import memory_migration_parser as parser_module
from app.services.memory_migration_intake import assess_memory_migration_intake
from app.services.memory_migration_parser import (
    FilesystemArtifactByteSource,
    InMemoryArtifactByteSource,
    MigrationArtifactByteSource,
    _is_special_member,
    _is_unsafe_member_name,
    parse_and_project,
)

EXPORTED_AT = datetime(2026, 6, 1, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Byte / fixture builders
# --------------------------------------------------------------------------- #
def _digest(data: bytes, algorithm: MigrationDigestAlgorithm) -> DeclaredArtifactDigest:
    value = hashlib.new(algorithm.value, data).hexdigest()
    return DeclaredArtifactDigest(algorithm=algorithm, value=value)


def _conversations_bytes(conversations: list[dict[str, Any]]) -> bytes:
    return json.dumps(conversations).encode("utf-8")


def _message_node(
    node_id: str,
    role: str,
    text: str | None,
    *,
    parent: str | None,
    children: list[str],
    create_time: float | None = 1.0,
    content_type: str = "text",
) -> dict[str, Any]:
    content: dict[str, Any] = {"content_type": content_type}
    if content_type == "text":
        content["parts"] = [text] if text is not None else []
    else:
        content["parts"] = []
    return {
        "id": node_id,
        "parent": parent,
        "children": children,
        "message": {
            "id": node_id,
            "author": {"role": role},
            "create_time": create_time,
            "content": content,
        },
    }


def _simple_conversation(
    conversation_id: str = "conv-1", **message_kwargs: Any
) -> dict[str, Any]:
    return {
        "conversation_id": conversation_id,
        "create_time": 100.0,
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["u1"]},
            "u1": _message_node(
                "u1", "user", "hello", parent="root", children=["a1"], create_time=101.0
            ),
            "a1": _message_node(
                "a1", "assistant", "hi", parent="u1", children=[], create_time=102.0
            ),
        },
    }


def _artifact(
    data: bytes,
    *,
    artifact_format: MigrationArtifactFormat = (
        MigrationArtifactFormat.CHATGPT_CONVERSATIONS_JSON
    ),
    container: MigrationContainerKind = MigrationContainerKind.SINGLE_FILE,
    path: str = "conversations.json",
    algorithm: MigrationDigestAlgorithm = MigrationDigestAlgorithm.SHA256,
    artifact_id: str = "artifact-1",
    byte_size: int | None = None,
    **overrides: Any,
) -> MigrationArtifactDescriptor:
    fields: dict[str, Any] = {
        "artifact_id": artifact_id,
        "declared_relative_path": path,
        "entry_kind": MigrationEntryKind.FILE,
        "artifact_format": artifact_format,
        "container": container,
        "declared_byte_size": len(data) if byte_size is None else byte_size,
        "declared_digest": _digest(data, algorithm),
    }
    fields.update(overrides)
    return MigrationArtifactDescriptor(**fields)


def _bundle(
    artifacts: list[MigrationArtifactDescriptor],
    *,
    custody: MigrationCustodyKind = MigrationCustodyKind.USER_ASSEMBLED_BUNDLE,
    **overrides: Any,
) -> MemoryMigrationBundle:
    provenance = MigrationProvenance(
        custody=custody,
        source=MemorySource(source_type=MemorySourceType.CHATGPT, source_id="export"),
        declared_exported_at=EXPORTED_AT,
    )
    fields: dict[str, Any] = {
        "bundle_id": "bundle-1",
        "provenance": provenance,
        "artifacts": artifacts,
    }
    fields.update(overrides)
    return MemoryMigrationBundle(**fields)


def _run(
    bundle: MemoryMigrationBundle,
    source_map: dict[str, bytes],
    *,
    assessment: Any | None = None,
) -> Any:
    resolved = assessment or assess_memory_migration_intake(bundle)
    return parse_and_project(bundle, resolved, InMemoryArtifactByteSource(source_map))


def _codes(result: Any) -> set[str]:
    return {d.code.value for d in result.diagnostics}


class _SpySource(MigrationArtifactByteSource):
    """A byte source that records how many times it was asked for bytes."""

    def __init__(self) -> None:
        self.calls = 0

    def read_artifact(self, artifact: MigrationArtifactDescriptor) -> bytes:
        self.calls += 1
        return b""


# =========================================================================== #
# The ready path
# =========================================================================== #
def test_a_ready_bundle_parses_into_candidates() -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})

    assert result.gate_permitted is True
    assert result.artifacts_read == 1
    assert result.candidate_count == 2
    roles = [c.provenance.source_role for c in result.candidates]
    assert MigrationCandidateRole.USER in roles
    assert MigrationCandidateRole.ASSISTANT in roles
    assert result.persisted is False
    assert result.imported is False


# =========================================================================== #
# Assessment gate (§26)
# =========================================================================== #
def test_blocked_assessment_reads_zero_bytes() -> None:
    # Missing declared digest -> blocked.
    artifact = _artifact(b"{}", byte_size=2)
    artifact = artifact.model_copy(update={"declared_digest": None})
    bundle = _bundle([artifact])
    assessment = assess_memory_migration_intake(bundle)
    assert assessment.ready_for_parsing is False

    spy = _SpySource()
    result = parse_and_project(bundle, assessment, spy)
    assert spy.calls == 0
    assert result.gate_permitted is False
    assert result.artifacts_read == 0
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ASSESSMENT_GATE_REJECTED.value in _codes(result)


def test_quarantined_assessment_reads_zero_bytes() -> None:
    data = _conversations_bytes([_simple_conversation()])
    artifact = _artifact(data, entry_kind=MigrationEntryKind.SYMLINK)
    bundle = _bundle([artifact])
    assessment = assess_memory_migration_intake(bundle)
    assert assessment.assessed_status.value == "quarantined"

    spy = _SpySource()
    result = parse_and_project(bundle, assessment, spy)
    assert spy.calls == 0
    assert result.gate_permitted is False


def test_ready_assessment_for_a_different_bundle_does_not_proceed() -> None:
    # The two bundles differ in a fingerprinted field (the artifact path), so the
    # assessment made about one authorizes nothing for the other, even though both
    # are independently ready.
    data = _conversations_bytes([_simple_conversation()])
    bundle_a = _bundle([_artifact(data, path="conversations.json")])
    bundle_b = _bundle([_artifact(data, path="other-conversations.json")])
    assessment_a = assess_memory_migration_intake(bundle_a)
    assert assessment_a.ready_for_parsing is True
    assert bundle_a.fingerprint() != bundle_b.fingerprint()

    spy = _SpySource()
    result = parse_and_project(bundle_b, assessment_a, spy)
    assert spy.calls == 0
    assert result.gate_permitted is False
    assert MigrationProjectionDiagnosticCode.STALE_ASSESSMENT.value in _codes(result)


def test_stale_assessment_after_declaration_change_does_not_proceed() -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data)])
    assessment = assess_memory_migration_intake(bundle)

    # Mutate the declaration after assessment: a new fingerprint, so the old
    # assessment authorizes nothing.
    changed_artifact = bundle.artifacts[0].model_copy(update={"declared_byte_size": len(data) + 1})
    changed_bundle = bundle.model_copy(update={"artifacts": [changed_artifact]})

    spy = _SpySource()
    result = parse_and_project(changed_bundle, assessment, spy)
    assert spy.calls == 0
    assert result.gate_permitted is False
    assert MigrationProjectionDiagnosticCode.STALE_ASSESSMENT.value in _codes(result)


def test_matching_ready_assessment_permits_parsing() -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data)])
    assessment = assess_memory_migration_intake(bundle)
    assert assessment.permits_parsing(bundle_fingerprint=bundle.fingerprint()) is True
    result = _run(bundle, {"artifact-1": data}, assessment=assessment)
    assert result.gate_permitted is True


# =========================================================================== #
# Integrity (§27)
# =========================================================================== #
@pytest.mark.parametrize(
    "algorithm",
    [MigrationDigestAlgorithm.SHA256, MigrationDigestAlgorithm.SHA512],
)
def test_accepted_digest_matches_actual_bytes(
    algorithm: MigrationDigestAlgorithm,
) -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data, algorithm=algorithm)])
    result = _run(bundle, {"artifact-1": data})
    assert len(result.integrity_results) == 1
    integrity = result.integrity_results[0]
    assert integrity.integrity_verified is True
    assert integrity.algorithm is algorithm
    assert integrity.observed_digest_value == integrity.declared_digest_value


def test_digest_mismatch_fails_closed() -> None:
    data = _conversations_bytes([_simple_conversation()])
    artifact = _artifact(data)
    tampered = artifact.model_copy(
        update={
            "declared_digest": DeclaredArtifactDigest(
                algorithm=MigrationDigestAlgorithm.SHA256, value="d" * 64
            )
        }
    )
    bundle = _bundle([tampered])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert result.integrity_results == []
    assert result.artifacts_read == 1
    assert MigrationProjectionDiagnosticCode.DIGEST_MISMATCH.value in _codes(result)


def test_actual_size_mismatch_is_surfaced() -> None:
    data = _conversations_bytes([_simple_conversation()])
    artifact = _artifact(data, byte_size=len(data) + 99)
    bundle = _bundle([artifact])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ACTUAL_SIZE_MISMATCH.value in _codes(result)


def test_declared_digest_object_is_not_mutated_and_stays_unverified() -> None:
    data = _conversations_bytes([_simple_conversation()])
    artifact = _artifact(data)
    bundle = _bundle([artifact])
    _run(bundle, {"artifact-1": data})
    # Phase 40E pins declared verification to False; Phase 40F must never flip it.
    assert bundle.artifacts[0].declared_digest.verified is False


def test_byte_integrity_never_upgrades_candidate_verification_state() -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count > 0
    assert all(
        c.verification_state is VerificationState.UNVERIFIED for c in result.candidates
    )


# =========================================================================== #
# Missing source
# =========================================================================== #
def test_missing_artifact_bytes_are_reported() -> None:
    data = _conversations_bytes([_simple_conversation()])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {})  # no bytes provided
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARTIFACT_SOURCE_MISSING.value in _codes(result)


# =========================================================================== #
# Archive handling (§28)
# =========================================================================== #
def _zip_bytes(members: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            archive.writestr(name, payload)
    return buffer.getvalue()


def _archive_bundle(zip_bytes: bytes) -> MemoryMigrationBundle:
    artifact = _artifact(
        zip_bytes,
        artifact_format=MigrationArtifactFormat.CHATGPT_EXPORT_ARCHIVE,
        container=MigrationContainerKind.ZIP_ARCHIVE,
        path="export.zip",
    )
    return _bundle([artifact], custody=MigrationCustodyKind.USER_REQUESTED_EXPORT)


def test_valid_chatgpt_export_archive_parses() -> None:
    inner = _conversations_bytes([_simple_conversation()])
    zip_bytes = _zip_bytes([("chat/conversations.json", inner), ("chat/notes.txt", b"x")])
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 2
    assert not _codes(result)


@pytest.mark.parametrize("member_name", ["../evil.json", "/abs/conversations.json"])
def test_archive_with_unsafe_member_path_fails_closed(member_name: str) -> None:
    inner = _conversations_bytes([_simple_conversation()])
    zip_bytes = _zip_bytes([(member_name, inner), ("conversations.json", inner)])
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION.value in _codes(result)


def test_archive_with_symlink_member_fails_closed() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.external_attr = (0o120777 & 0xFFFF) << 16  # S_IFLNK
        archive.writestr(info, "/etc/passwd")
        archive.writestr("conversations.json", _conversations_bytes([_simple_conversation()]))
    zip_bytes = buffer.getvalue()
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION.value in _codes(result)


def test_encrypted_member_is_a_safety_violation() -> None:
    # stdlib zipfile cannot write an encrypted member, so the encryption branch is
    # covered by screening a crafted member directly. An encrypted member sets the
    # low general-purpose flag bit.
    info = zipfile.ZipInfo("conversations.json")
    info.flag_bits |= 0x1
    violation = parser_module._member_safety_violation(info)
    assert violation is not None
    code, _message = violation
    assert code is MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION


def test_oversized_member_is_a_bound_violation(monkeypatch: Any) -> None:
    monkeypatch.setattr(parser_module, "MAX_ARCHIVE_MEMBER_UNCOMPRESSED_BYTES", 4)
    info = zipfile.ZipInfo("big.txt")
    info.file_size = 1000
    violation = parser_module._member_safety_violation(info)
    assert violation is not None
    assert violation[0] is MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED


def test_archive_exceeding_member_count_fails_closed(monkeypatch: Any) -> None:
    monkeypatch.setattr(parser_module, "MAX_ARCHIVE_MEMBERS", 2)
    inner = _conversations_bytes([_simple_conversation()])
    zip_bytes = _zip_bytes(
        [("conversations.json", inner), ("a.txt", b"a"), ("b.txt", b"b")]
    )
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED.value in _codes(result)


def test_archive_exceeding_total_uncompressed_size_fails_closed(monkeypatch: Any) -> None:
    monkeypatch.setattr(parser_module, "MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES", 16)
    inner = _conversations_bytes([_simple_conversation()])
    zip_bytes = _zip_bytes([("conversations.json", inner)])
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARCHIVE_BOUND_EXCEEDED.value in _codes(result)


def test_archive_missing_conversations_member_is_reported() -> None:
    zip_bytes = _zip_bytes([("notes.txt", b"just notes")])
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.ARCHIVE_MEMBER_MISSING.value in _codes(result)


def test_archive_malformed_conversations_member_is_reported() -> None:
    zip_bytes = _zip_bytes([("conversations.json", b"{not json")])
    bundle = _archive_bundle(zip_bytes)
    result = _run(bundle, {"artifact-1": zip_bytes})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.MALFORMED_JSON.value in _codes(result)


def test_archive_rejects_duplicate_conversations_members() -> None:
    # Multiple plausible payloads are ambiguous and must fail closed rather than
    # selecting one according to attacker-controlled names or insertion order.
    conv_a = _conversations_bytes(
        [{"conversation_id": "c", "mapping": {"u1": _message_node("u1", "user", "from-a", parent=None, children=[])}}]
    )
    conv_z = _conversations_bytes(
        [{"conversation_id": "c", "mapping": {"u1": _message_node("u1", "user", "from-z", parent=None, children=[])}}]
    )

    def parse(order: list[tuple[str, bytes]]):
        zip_bytes = _zip_bytes(order)
        return _run(_archive_bundle(zip_bytes), {"artifact-1": zip_bytes})

    forward = parse([("z/conversations.json", conv_z), ("a/conversations.json", conv_a)])
    reverse = parse([("a/conversations.json", conv_a), ("z/conversations.json", conv_z)])
    for result in (forward, reverse):
        assert result.candidates == []
        assert (
            MigrationProjectionDiagnosticCode.ARCHIVE_SAFETY_VIOLATION.value
            in _codes(result)
        )


def test_parser_never_extracts_an_archive_to_disk() -> None:
    # "extracted to disk" would mean calling extractall or writing members out.
    source = Path(inspect.getfile(parser_module)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "extractall" not in called
    assert "extract" not in called


def test_unsafe_member_and_special_member_predicates() -> None:
    assert _is_unsafe_member_name("../x")
    assert _is_unsafe_member_name("/abs")
    assert _is_unsafe_member_name("C:/win")
    assert _is_unsafe_member_name("a\x00b")
    assert not _is_unsafe_member_name("chat/conversations.json")

    link = zipfile.ZipInfo("link")
    link.external_attr = (0o120777 & 0xFFFF) << 16
    assert _is_special_member(link)
    plain = zipfile.ZipInfo("file")
    assert not _is_special_member(plain)


# =========================================================================== #
# ChatGPT export parsing (§29)
# =========================================================================== #
def test_multiple_conversations_all_parse() -> None:
    data = _conversations_bytes(
        [_simple_conversation("conv-1"), _simple_conversation("conv-2")]
    )
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 4
    containers = {c.provenance.source_container_id for c in result.candidates}
    assert containers == {"conv-1", "conv-2"}


def test_system_tool_and_developer_roles_are_skipped_with_a_count() -> None:
    conversation = {
        "conversation_id": "conv-1",
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["s1", "u1"]},
            "s1": _message_node("s1", "system", "secret sys", parent="root", children=[]),
            "u1": _message_node("u1", "user", "hello", parent="root", children=[]),
        },
    }
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 1
    assert result.candidates[0].provenance.source_role is MigrationCandidateRole.USER
    role_diags = [
        d
        for d in result.diagnostics
        if d.code is MigrationProjectionDiagnosticCode.UNSUPPORTED_MESSAGE_ROLE
    ]
    assert role_diags and role_diags[0].count == 1
    # The skipped system content never leaks into any candidate.
    assert all("secret sys" not in c.content for c in result.candidates)


def test_non_text_and_empty_messages_are_skipped() -> None:
    conversation = {
        "conversation_id": "conv-1",
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["u1", "u2", "u3"]},
            "u1": _message_node("u1", "user", None, parent="root", children=[], content_type="image_asset_pointer"),
            "u2": _message_node("u2", "user", "   ", parent="root", children=[]),
            "u3": _message_node("u3", "user", "real", parent="root", children=[]),
        },
    }
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 1
    codes = _codes(result)
    assert MigrationProjectionDiagnosticCode.NON_TEXT_CONTENT_SKIPPED.value in codes
    assert MigrationProjectionDiagnosticCode.EMPTY_CONTENT_SKIPPED.value in codes


def test_malformed_message_is_skipped_not_repaired() -> None:
    conversation = {
        "conversation_id": "conv-1",
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["b1", "u1"]},
            "b1": {"id": "b1", "parent": "root", "children": [], "message": {"id": "b1"}},
            "u1": _message_node("u1", "user", "hello", parent="root", children=[]),
        },
    }
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 1
    assert MigrationProjectionDiagnosticCode.MALFORMED_MESSAGE.value in _codes(result)


def test_missing_timestamp_is_carried_as_none() -> None:
    conversation = {
        "conversation_id": "conv-1",
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["u1"]},
            "u1": _message_node("u1", "user", "hello", parent="root", children=[], create_time=None),
        },
    }
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 1
    assert result.candidates[0].provenance.declared_source_timestamp is None


def test_conversation_without_identifier_is_skipped() -> None:
    conversation = {
        "mapping": {
            "u1": _message_node("u1", "user", "hello", parent=None, children=[]),
        }
    }
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.MALFORMED_CONVERSATION.value in _codes(result)


def test_non_list_conversations_payload_is_unsupported_shape() -> None:
    data = json.dumps({"not": "a list"}).encode("utf-8")
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE.value in _codes(result)


def test_repeated_parsing_is_deterministic() -> None:
    data = _conversations_bytes(
        [_simple_conversation("conv-1"), _simple_conversation("conv-2")]
    )
    bundle = _bundle([_artifact(data)])
    first = _run(bundle, {"artifact-1": data})
    second = _run(bundle, {"artifact-1": data})
    assert [c.candidate_id for c in first.candidates] == [
        c.candidate_id for c in second.candidates
    ]
    assert [c.sort_key() for c in first.candidates] == [
        c.sort_key() for c in second.candidates
    ]


def test_message_order_is_independent_of_mapping_insertion_order() -> None:
    def build(order: list[str]) -> dict[str, Any]:
        nodes = {
            "root": {"id": "root", "message": None, "parent": None, "children": ["u1"]},
            "u1": _message_node("u1", "user", "first", parent="root", children=["a1"], create_time=1.0),
            "a1": _message_node("a1", "assistant", "second", parent="u1", children=[], create_time=2.0),
        }
        return {"conversation_id": "conv-1", "mapping": {key: nodes[key] for key in order}}

    forward = _conversations_bytes([build(["root", "u1", "a1"])])
    scrambled = _conversations_bytes([build(["a1", "root", "u1"])])
    r1 = _run(_bundle([_artifact(forward)]), {"artifact-1": forward})
    r2 = _run(_bundle([_artifact(scrambled)]), {"artifact-1": scrambled})
    assert [c.content for c in r1.candidates] == ["first", "second"]
    assert [c.content for c in r2.candidates] == ["first", "second"]


def test_candidate_content_carries_only_message_text() -> None:
    # Conversation title / metadata must not leak into candidate content.
    conversation = _simple_conversation("conv-1")
    conversation["title"] = "SENSITIVE ACCOUNT NAME"
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    assert all("SENSITIVE" not in c.content for c in result.candidates)
    assert {c.content for c in result.candidates} == {"hello", "hi"}


# =========================================================================== #
# Curated / plain-text formats (§30)
# =========================================================================== #
def test_plain_text_document_becomes_one_document_candidate() -> None:
    data = "a curated note the user wrote".encode("utf-8")
    artifact = _artifact(
        data,
        artifact_format=MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT,
        path="note.txt",
    )
    bundle = _bundle([artifact])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 1
    assert result.candidates[0].provenance.source_role is MigrationCandidateRole.DOCUMENT


def test_curated_json_bundle_parses_entries() -> None:
    payload = {
        "schema_version": "memory-migration-curated.v1",
        "entries": [
            {"entry_id": "e1", "text": "first entry"},
            {"entry_id": "e2", "text": "second entry", "role": "assistant"},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    artifact = _artifact(
        data,
        artifact_format=MigrationArtifactFormat.CURATED_JSON_BUNDLE,
        path="curated.json",
    )
    bundle = _bundle([artifact])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 2
    entries = {c.provenance.source_entry_id for c in result.candidates}
    assert entries == {"e1", "e2"}


def test_curated_json_bundle_rejects_authority_fields() -> None:
    payload = {
        "schema_version": "memory-migration-curated.v1",
        "entries": [{"entry_id": "e1", "text": "x", "verified": True}],
    }
    data = json.dumps(payload).encode("utf-8")
    artifact = _artifact(
        data,
        artifact_format=MigrationArtifactFormat.CURATED_JSON_BUNDLE,
        path="curated.json",
    )
    bundle = _bundle([artifact])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.UNSUPPORTED_JSON_SHAPE.value in _codes(result)


def test_invalid_utf8_document_is_a_decode_error() -> None:
    data = b"\xff\xfe\x00bad"
    artifact = _artifact(
        data,
        artifact_format=MigrationArtifactFormat.PLAIN_TEXT_DOCUMENT,
        path="note.txt",
    )
    bundle = _bundle([artifact])
    result = _run(bundle, {"artifact-1": data})
    assert result.candidate_count == 0
    assert MigrationProjectionDiagnosticCode.DECODE_ERROR.value in _codes(result)


# =========================================================================== #
# Value safety / determinism of the result
# =========================================================================== #
def test_no_diagnostic_message_echoes_exported_content() -> None:
    conversation = _simple_conversation("conv-1")
    conversation["mapping"]["s1"] = _message_node(
        "s1", "system", "TOP SECRET SYSTEM PROMPT", parent="root", children=[]
    )
    conversation["mapping"]["root"]["children"].append("s1")
    data = _conversations_bytes([conversation])
    bundle = _bundle([_artifact(data)])
    result = _run(bundle, {"artifact-1": data})
    for diagnostic in result.diagnostics:
        assert "TOP SECRET" not in diagnostic.message


def test_filesystem_source_rejects_escaping_paths(tmp_path: Path) -> None:
    source = FilesystemArtifactByteSource(tmp_path)
    artifact = _artifact(b"data", path="../escape.txt")
    with pytest.raises(parser_module.MigrationArtifactSourceError):
        source.read_artifact(artifact)


def test_filesystem_source_reads_declared_file(tmp_path: Path) -> None:
    data = _conversations_bytes([_simple_conversation()])
    (tmp_path / "conversations.json").write_bytes(data)
    bundle = _bundle([_artifact(data)])
    assessment = assess_memory_migration_intake(bundle)
    result = parse_and_project(bundle, assessment, FilesystemArtifactByteSource(tmp_path))
    assert result.candidate_count == 2
