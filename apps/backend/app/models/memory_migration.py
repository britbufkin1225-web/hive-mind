"""Phase 40E — Memory Migration intake contract types (``memory-migration.v1``).

Contract and schema foundation only. These are the stable **wire shapes** for the
memory-migration track sequenced by Phase 40D.5
(``docs/planning/phase-40d-5-roadmap-reconciliation-memory-migration-pivot.md``).
This module adds **NO** migration behavior: no export parsing, no archive
extraction, no byte access, no filesystem/network/Git access, no candidate
projection, no persistence, no verified import, no endpoint, no frontend, and no
AI/LLM integration. It defines *shapes* and their bounded validation only —
exactly as Phase 37B defined ``active-memory.v1`` and Phase 40B defined
``grounded-synthesis.v1`` before any logic ran.

Conventions (kept identical to ``active_memory.py`` / ``grounded_synthesis.py``
so every contract layer reads the same):

* Enums are :class:`enum.StrEnum` with ``UPPER_SNAKE`` member names whose
  serialized value is the ``snake_case`` string literal. Because these are
  ``StrEnum``, the serialized value *is* that literal — it is the stable wire
  contract.
* Every model sets ``model_config = ConfigDict(extra="forbid")``. Unknown fields
  are rejected rather than silently absorbed, which is what keeps a
  parser-specific, filesystem-specific, or credential-shaped field from ever
  leaking into an intake declaration through a permissive schema.
* Caller-supplied free text and every collection carry defensive upper bounds
  (``MAX_MIGRATION_*``), matching the Phase 18B / 37B / 40B bounded-field
  discipline: oversized or unbounded input is rejected at the contract edge.
* Stable Active Memory *semantic* vocabularies are reused rather than duplicated
  (:class:`~app.models.active_memory.MemorySource`,
  :class:`~app.models.active_memory.MemoryScope`,
  :class:`~app.models.active_memory.LifecycleState`,
  :class:`~app.models.active_memory.VerificationState`). Their permissive
  *record* models (``MemoryRecord``, ``EvidenceRecord``) are deliberately **not**
  reused: those describe material Hive|Mind already holds and can reason about,
  and admitting unparsed migration material into them would let raw intake
  masquerade as memory.

Design rationale for every significant decision is recorded inline. The headline
decisions:

* **Declared, never verified.** Every field on every model in this module is a
  *declaration* by the user or by the tool that produced the export. Phase 40E
  opens no artifact and reads no byte, so it cannot confirm a size, a digest, a
  path, an entry type, or a format. :class:`DeclaredArtifactDigest` therefore
  pins ``verified`` to ``False``, and the whole family is named "declared" at
  every field it can be — the contract must not let unverified metadata be read
  as a verified fact.
* **Raw migration artifacts are not memory and not evidence.**
  :class:`MemoryMigrationBundle` pins ``is_memory`` and ``is_verified_evidence``
  to ``False`` and rejects being turned off. A bundle is a bounded description of
  material the user handed over; it is not a claim, not a record, and not proof
  of anything.
* **The lifecycle stops at the parsing boundary.**
  :class:`MigrationIntakeStatus` carries exactly four members —
  ``declared``, ``ready_for_parsing``, ``blocked``, ``quarantined``. There is
  deliberately no ``parsed``, ``projected``, ``reviewed``, ``approved``,
  ``persisted``, ``verified``, or ``active`` state anywhere in this phase: those
  describe work Phase 40F and Phase 40G do, and a vocabulary that could express
  them here would let an intake declaration claim an outcome no code produces.
* **A bundle cannot declare its own readiness.**
  ``MemoryMigrationBundle.intake_status`` is pinned to ``declared`` and rejects
  any other value. Readiness is *derived* by the Phase 40E assessment
  (:mod:`app.services.memory_migration_intake`) from the bundle's actual
  contents — a caller-asserted ``ready_for_parsing`` would be exactly the silent
  authority escalation the Phase 40A/40B boundary forbids.
* **Migration provenance is its own strict contract.** It deliberately does not
  reuse ``ProvenanceChain`` (``app.models.hive_models``), which is a *graph*
  view: derived, advisory, node/edge-shaped, and permissive about missing
  origins because a graph tolerates partial derivation. Pre-ingestion custody is
  the opposite: it must be complete, mandatory, and refuse to describe material
  Hive|Mind acquired for itself. Stretching the graph contract to carry custody
  would make an advisory structure load-bearing for a trust boundary.
* **Identity is content-derived and deterministic.** Nothing here reads a clock,
  generates a random identifier, or touches the environment.
  :func:`derive_migration_id`, :func:`derive_artifact_fingerprint`, and
  :func:`derive_bundle_fingerprint` fold canonical UTF-8 JSON material through
  SHA-256, so identical declarations always produce identical identities.

Contract shape versus intake safety — a deliberate split. The models here
enforce *representability*: is this value bounded, non-empty, and recordable at
all? They do **not** judge safety. Whether a declared path traverses, whether an
entry kind is structurally unsafe, whether a format is parseable, and whether a
declared size fits policy are decided by the Phase 40E assessment, which reports
them as typed ``blocked``/``quarantined`` diagnostics. Rejecting unsafe material
at the model edge would raise an untyped ``ValidationError`` and destroy the very
diagnostics the intake boundary exists to produce.

No migration runtime exists after this phase. Declaring a shape is not importing
anything; nothing here parses, extracts, projects, reviews, persists, or
verifies — those are Phase 40F and Phase 40G.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.active_memory import (
    LifecycleState,
    MemoryScope,
    MemorySource,
    VerificationState,
)
from app.services.validation import assert_within_nesting_depth

# --------------------------------------------------------------------------- #
# Contract version.
#
# A stable *wire* version for the whole memory-migration contract family,
# decoupled from the application/package version so the type contract can evolve
# on its own cadence — the same decision recorded for
# ``ACTIVE_MEMORY_CONTRACT_VERSION`` and ``GROUNDED_SYNTHESIS_CONTRACT_VERSION``.
# It is a fixed literal, not derived from a package version, so a client can pin
# against it deterministically. Every top-level record carries it and rejects any
# other value rather than guessing.
# --------------------------------------------------------------------------- #
MEMORY_MIGRATION_CONTRACT_VERSION = "memory-migration.v1"


# --------------------------------------------------------------------------- #
# Bounded free-text / collection / metadata limits.
#
# Defensive upper bounds for caller-supplied fields, mirroring the Phase 18B,
# 37B and 40B rationale: they reject pathologically large input at the contract
# boundary without constraining any realistic value.
#
# ``MAX_MIGRATION_PATH_LENGTH`` is 4096 rather than the 1024-ish figure used for
# labels: a declared path inside a real ChatGPT export archive can be deeply
# nested, and a path is *identity-bearing* material this phase must never
# rewrite. A bound that rejected a legitimate deep path would push a caller
# toward trimming it, which is precisely the silent identity mutation the phase
# forbids.
#
# ``MAX_MIGRATION_BUNDLE_ARTIFACTS`` (2048) is the *contract* ceiling on how many
# artifacts a bundle can even represent. The narrower *policy* ceiling that
# decides intake readiness lives in the assessment service, so tightening policy
# never requires a contract change.
# --------------------------------------------------------------------------- #
MAX_MIGRATION_ID_LENGTH = 256
MAX_MIGRATION_LABEL_LENGTH = 512
MAX_MIGRATION_SUMMARY_LENGTH = 2048
MAX_MIGRATION_PATH_LENGTH = 4096
MAX_MIGRATION_MEDIA_TYPE_LENGTH = 255
MAX_MIGRATION_DIGEST_LENGTH = 128

MAX_MIGRATION_BUNDLE_ARTIFACTS = 2048
MAX_MIGRATION_COLLECTION_ITEMS = 256

MAX_MIGRATION_METADATA_ENTRIES = 32
MAX_MIGRATION_METADATA_KEY_LENGTH = 128
MAX_MIGRATION_METADATA_VALUE_LENGTH = 1024
# Metadata is a shallow, inspectable bag — never an arbitrary nested document.
# Four levels covers every realistic annotation while rejecting the
# recursion-shaped payloads Phase 18D named (see ``assert_within_nesting_depth``).
MAX_MIGRATION_METADATA_DEPTH = 4
MAX_MIGRATION_METADATA_CONTAINER_ITEMS = 32
MAX_MIGRATION_METADATA_TOTAL_NODES = 256

# Keys that must never ride into an intake declaration. The Phase 40B forbidden
# set is extended with the two categories specific to migration: credential-shaped
# keys (an export is fetched from an account, and a caller might helpfully attach
# the token it used) and byte-bearing keys (``content``/``body``/``raw`` would put
# the artifact's actual contents inside a metadata bag, turning a *declaration*
# into an unparsed payload and defeating the entire declared-metadata boundary).
FORBIDDEN_MIGRATION_METADATA_KEYS = frozenset(
    {
        "access_token",
        "api_base",
        "api_key",
        "authorization",
        "body",
        "content",
        "cookie",
        "credentials",
        "endpoint_url",
        "file_bytes",
        "model",
        "password",
        "payload",
        "prompt",
        "provider",
        "raw",
        "raw_content",
        "refresh_token",
        "secret",
        "session_token",
        "system_prompt",
        "token",
    }
)


# =========================================================================== #
# Enumerations (closed wire vocabularies)
# =========================================================================== #
class MigrationIntakeStatus(StrEnum):
    """The complete Phase 40E intake lifecycle — four members, no more.

    ``declared`` is the only state a caller may author: it means "the user has
    handed this over and described it". The other three are *derived* by the
    Phase 40E assessment:

    * ``ready_for_parsing`` — the declaration is well-formed, in policy, and
      structurally safe enough that Phase 40F may attempt to parse it. It is
      **not** a statement that the artifacts are safe, correct, or truthful;
      nothing has been read.
    * ``blocked`` — the declaration is recognized but cannot proceed (an
      unsupported format, a missing declared digest, a policy bound exceeded).
      Recoverable by the user changing the declaration.
    * ``quarantined`` — the declaration describes structurally unsafe material
      (a traversing or absolute path, a symlink or device entry, an origin
      Hive|Mind refuses to accept). Not recoverable by re-declaration; the
      material itself is the problem.

    Deliberately **absent**: ``parsed``, ``projected``, ``reviewed``,
    ``approved``, ``persisted``, ``verified``, ``imported``, and ``active``.
    Phase 40E cannot reach any of them — parsing is Phase 40F and reviewed
    persistence is the exclusive Phase 40G boundary — so a vocabulary able to
    express them would let a declaration claim an outcome no code in this phase
    produces.
    """

    DECLARED = "declared"
    READY_FOR_PARSING = "ready_for_parsing"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"


class MigrationCustodyKind(StrEnum):
    """How the user came to possess the material they are handing over.

    Closed rather than free text because the intake boundary branches on it: two
    members are recognized specifically so they can be **refused**.

    * ``user_requested_export`` — the user asked a provider for their own data
      export and downloaded it.
    * ``user_assembled_bundle`` — the user curated the bundle themselves.
    * ``user_provided_document`` — the user handed over an individual document.
    * ``third_party_transfer`` — material obtained from someone other than the
      user whose memory it is.
    * ``automated_account_link`` — material a tool pulled directly from a live
      account.

    The last two are representable **on purpose**. Hive|Mind claims no direct,
    account-to-account access to any provider's private system memory
    (Phase 40D.5 §7), and the honest way to hold that line is to be able to
    *name* the custody it refuses and quarantine it with a typed diagnostic —
    not to omit the concept and silently accept whatever arrives wearing an
    approved label.
    """

    USER_REQUESTED_EXPORT = "user_requested_export"
    USER_ASSEMBLED_BUNDLE = "user_assembled_bundle"
    USER_PROVIDED_DOCUMENT = "user_provided_document"
    THIRD_PARTY_TRANSFER = "third_party_transfer"
    AUTOMATED_ACCOUNT_LINK = "automated_account_link"


class MigrationArtifactFormat(StrEnum):
    """Closed catalog of artifact formats Phase 40E can *recognize*.

    Recognition is not support. Membership here means the intake boundary knows
    what the caller is describing well enough to reason about it; whether a
    future parser exists for it is a *policy* question answered by the assessment
    service, so a format can be recognized and still fail closed as
    ``blocked``. Splitting the two is what lets a diagnostic say "this is an
    Obsidian vault export and Hive|Mind has no parser for it" instead of the
    uninformative "unknown".

    ``unrecognized`` is a member rather than an absence so a caller can declare
    honestly that they do not know what the artifact is. It is always blocking —
    material Hive|Mind cannot name is material it must not hand to a parser.
    """

    CHATGPT_EXPORT_ARCHIVE = "chatgpt_export_archive"
    CHATGPT_CONVERSATIONS_JSON = "chatgpt_conversations_json"
    CURATED_MARKDOWN_BUNDLE = "curated_markdown_bundle"
    CURATED_JSON_BUNDLE = "curated_json_bundle"
    PLAIN_TEXT_DOCUMENT = "plain_text_document"
    OBSIDIAN_VAULT_EXPORT = "obsidian_vault_export"
    UNRECOGNIZED = "unrecognized"


class MigrationContainerKind(StrEnum):
    """How the artifact's bytes are packaged.

    Kept separate from :class:`MigrationArtifactFormat` because packaging and
    content are independent safety axes: a JSON export and a Markdown bundle
    raise the same archive-extraction risks when both arrive zipped, and the same
    format may arrive either way. Folding them into one enum would force a
    combinatorial vocabulary and make the archive-specific rules impossible to
    state once.
    """

    SINGLE_FILE = "single_file"
    ZIP_ARCHIVE = "zip_archive"
    DIRECTORY_TREE = "directory_tree"


class MigrationEntryKind(StrEnum):
    """The declared filesystem entry type of one artifact.

    A closed vocabulary covering the entry types a real export or curated bundle
    can present. The non-``file`` members exist so the intake boundary can
    *recognize and refuse* them rather than being surprised later: a symlink or
    hardlink can point outside the intake tree, and a device/socket/FIFO entry is
    not readable content at all. Every one of them is structurally unsafe for
    intake and quarantines.

    ``unknown`` is included because a caller enumerating an archive may genuinely
    be unable to determine an entry's type; declaring that honestly must be
    possible, and it fails closed.
    """

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    HARDLINK = "hardlink"
    DEVICE = "device"
    SOCKET = "socket"
    FIFO = "fifo"
    UNKNOWN = "unknown"


class MigrationDigestAlgorithm(StrEnum):
    """Digest algorithms a declaration may name.

    ``md5`` and ``sha1`` are representable **on purpose**, for the same reason
    the refused custody kinds are: an export tool may well have emitted one, and
    the honest response is a typed "this algorithm is too weak to anchor an
    integrity claim" diagnostic rather than a schema rejection the user cannot
    interpret. Which algorithms are *accepted* is assessment policy, not contract
    shape.
    """

    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA1 = "sha1"
    MD5 = "md5"


# =========================================================================== #
# Shared bounded-validation helpers
#
# Small, pure, reusable checks so every model in the family enforces the same
# rules with the same error text. None of them reads external state.
# =========================================================================== #
def _require_int(value: Any) -> Any:
    """Require an actual ``int`` where an integer is expected.

    Pydantic's lax mode accepts booleans, numeric strings, and integral floats.
    Declared counts and byte sizes are safety inputs, so silently converting any
    of those would make the assessment judge a value the caller did not actually
    declare as an integer.
    """

    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        raise ValueError("integer field must be an integer")
    return value


def _require_bool(value: Any) -> Any:
    """Reject a non-``bool`` supplied where a flag is expected.

    The mirror of :func:`_require_int`: ``0``/``1`` must not become a safety flag,
    because these flags carry the phase's load-bearing claims (``is_memory``,
    ``is_verified_evidence``, ``user_provided``) and must be explicit.
    """

    if not isinstance(value, bool):
        raise ValueError("flag field must be a boolean")
    return value


def _clean_required_text(value: str, label: str) -> str:
    """Strip and reject blank/whitespace-only required text.

    Applied to identifiers and labels only — never to a declared path. See
    :meth:`MigrationArtifactDescriptor._path_is_representable` for why
    identity-bearing material is left byte-for-byte intact.
    """

    text = value.strip()
    if not text:
        raise ValueError(f"{label} must not be empty or whitespace-only")
    return text


def _validate_bounded_metadata(value: dict[str, Any]) -> dict[str, Any]:
    """Bound a free-form metadata bag: entries, key length, value length, depth.

    Metadata stays the forward-compatible escape hatch used across the API, but
    it is never an unbounded or deeply nested document, and it is never a place
    to smuggle artifact bytes or a credential (see
    :data:`FORBIDDEN_MIGRATION_METADATA_KEYS`).
    """

    if len(value) > MAX_MIGRATION_METADATA_ENTRIES:
        raise ValueError(
            f"metadata exceeds the {MAX_MIGRATION_METADATA_ENTRIES} entry limit"
        )
    assert_within_nesting_depth(value, MAX_MIGRATION_METADATA_DEPTH)
    nodes_seen = 0
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        nodes_seen += 1
        if nodes_seen > MAX_MIGRATION_METADATA_TOTAL_NODES:
            raise ValueError(
                "metadata exceeds the "
                f"{MAX_MIGRATION_METADATA_TOTAL_NODES} total-node limit"
            )
        if isinstance(item, dict):
            if len(item) > MAX_MIGRATION_METADATA_CONTAINER_ITEMS:
                raise ValueError(
                    "metadata container exceeds the "
                    f"{MAX_MIGRATION_METADATA_CONTAINER_ITEMS} item limit"
                )
            for key, nested in item.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("metadata keys must be non-empty strings")
                if len(key) > MAX_MIGRATION_METADATA_KEY_LENGTH:
                    raise ValueError(
                        "metadata key exceeds the "
                        f"{MAX_MIGRATION_METADATA_KEY_LENGTH} character limit"
                    )
                normalized_key = key.strip().lower().replace("-", "_")
                if normalized_key in FORBIDDEN_MIGRATION_METADATA_KEYS:
                    raise ValueError(
                        f"credential/content metadata key {key!r} is not permitted"
                    )
                stack.append(nested)
        elif isinstance(item, list):
            if len(item) > MAX_MIGRATION_METADATA_CONTAINER_ITEMS:
                raise ValueError(
                    "metadata container exceeds the "
                    f"{MAX_MIGRATION_METADATA_CONTAINER_ITEMS} item limit"
                )
            stack.extend(item)
        elif isinstance(item, str):
            if len(item) > MAX_MIGRATION_METADATA_VALUE_LENGTH:
                raise ValueError(
                    "metadata value exceeds the "
                    f"{MAX_MIGRATION_METADATA_VALUE_LENGTH} character limit"
                )
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("metadata numeric values must be finite")
        elif item is not None and not isinstance(item, (bool, int)):
            raise ValueError(
                "metadata values must be JSON-compatible scalars or containers"
            )
    return value


def _validate_contract_version(value: str) -> str:
    """Reject any schema version other than the one this module implements."""

    if value != MEMORY_MIGRATION_CONTRACT_VERSION:
        raise ValueError(
            f"unsupported schema_version {value!r}; "
            f"expected {MEMORY_MIGRATION_CONTRACT_VERSION!r}"
        )
    return value


# --------------------------------------------------------------------------- #
# Deterministic identity derivation.
#
# Canonical UTF-8 JSON material folded through SHA-256, with a *narrow,
# documented* normalization: NFC on the readable prefix and on each supplied
# part, plus surrounding-whitespace stripping on each part. Nothing else is
# touched — no case folding, no path separator rewriting, no Unicode
# compatibility folding (NFKC) — because each of those would map two materially
# different declarations onto one identity.
#
# ``json.dumps`` over a list is what makes the material unambiguous: a plain
# delimiter join would let a part *containing* the delimiter forge a different
# part boundary and collide with an unrelated declaration.
# --------------------------------------------------------------------------- #
_DIGEST_PREFIX_LENGTH = 24


def _canonical_material(parts: list[Any]) -> bytes:
    """Serialize derivation material canonically and deterministically."""

    return json.dumps(
        parts, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def derive_migration_id(prefix: str, *parts: str) -> str:
    """Derive a stable identifier from explicitly-normalized caller inputs.

    Follows the existing repository's readable-prefix plus bounded SHA-256
    convention (``derive_grounded_synthesis_id``). It is a pure function of its
    arguments — no clock, no randomness, no environment — so the same inputs
    always yield the same id. Callers that already own an identifier should keep
    using it; this exists only so a caller that needs a derived one does not
    invent an ad hoc (or random) scheme.
    """

    clean_prefix = unicodedata.normalize(
        "NFC", _clean_required_text(prefix, "identifier prefix")
    )
    max_prefix_length = MAX_MIGRATION_ID_LENGTH - (_DIGEST_PREFIX_LENGTH + 1)
    if len(clean_prefix) > max_prefix_length:
        raise ValueError(
            f"identifier prefix exceeds the {max_prefix_length} character limit"
        )
    if not parts:
        raise ValueError("identifier derivation requires at least one input part")
    if len(parts) > MAX_MIGRATION_COLLECTION_ITEMS:
        raise ValueError(
            "identifier derivation exceeds the "
            f"{MAX_MIGRATION_COLLECTION_ITEMS} input-part limit"
        )
    normalized = [
        unicodedata.normalize("NFC", _clean_required_text(part, "identifier part"))
        for part in parts
    ]
    digest = hashlib.sha256(_canonical_material(normalized)).hexdigest()
    return f"{clean_prefix}-{digest[:_DIGEST_PREFIX_LENGTH]}"


def _canonical_datetime(value: datetime | None) -> str | None:
    """Render a caller-supplied timestamp canonically for identity material.

    ``isoformat()`` on the value as given: no timezone coercion and no clock
    read. A naive and an aware timestamp are *different declarations* and must
    fingerprint differently, so normalizing one into the other would erase a real
    difference in what the caller stated.
    """

    return None if value is None else value.isoformat()


# =========================================================================== #
# Shared model config
# =========================================================================== #
class _MemoryMigrationModel(BaseModel):
    """Shared config for every model in the family.

    ``extra="forbid"`` is the load-bearing setting: it is what guarantees a
    byte-bearing field (``content``, ``bytes``, ``data``), a credential, or a
    parser directive cannot ride into an intake declaration on an unknown key.
    """

    model_config = ConfigDict(extra="forbid")


# =========================================================================== #
# Declared digest
# =========================================================================== #
# Hex-character length each algorithm's output occupies. Declared here rather
# than computed from ``hashlib`` so the contract states the expectation
# explicitly and does not depend on which algorithms a given Python build happens
# to provide (``md5``/``sha1`` are unavailable under some FIPS-enforcing builds,
# and a contract must not change shape with the interpreter it runs on).
DIGEST_HEX_LENGTHS: dict[MigrationDigestAlgorithm, int] = {
    MigrationDigestAlgorithm.SHA256: 64,
    MigrationDigestAlgorithm.SHA512: 128,
    MigrationDigestAlgorithm.SHA1: 40,
    MigrationDigestAlgorithm.MD5: 32,
}


class DeclaredArtifactDigest(_MemoryMigrationModel):
    """A digest the *caller* declares for an artifact — explicitly unverified.

    ``verified`` is pinned ``False`` and rejects being turned on. That is the
    structural expression of the Phase 40E boundary: verifying a digest requires
    reading the artifact's bytes and recomputing the hash, and Phase 40E reads no
    bytes. A later phase that actually recomputes may record a verified digest —
    under its own contract, not by flipping a flag on a declaration.

    ``value`` must be lowercase hexadecimal of the length the named algorithm
    produces. Requiring it here is *representability*, not verification: a digest
    of the wrong shape cannot anchor any future integrity check, and accepting it
    would let a bundle carry an integrity-sounding field that no later phase
    could ever compare against.
    """

    algorithm: MigrationDigestAlgorithm
    value: str = Field(min_length=1, max_length=MAX_MIGRATION_DIGEST_LENGTH)
    verified: bool = False

    @field_validator("verified", mode="before")
    @classmethod
    def _flag_is_boolean(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("value")
    @classmethod
    def _digest_is_lowercase_hex(cls, value: str) -> str:
        text = _clean_required_text(value, "digest value")
        # A digest is an integrity reference, not a free-form label. Requiring
        # lowercase hex keeps it comparable byte-for-byte across producers and
        # stops arbitrary text riding in under an integrity-sounding name — the
        # same rule ``GroundingEvidenceReference.content_digest`` applies.
        if any(char not in "0123456789abcdef" for char in text):
            raise ValueError("digest value must be lowercase hexadecimal")
        return text

    @model_validator(mode="after")
    def _validate_digest(self) -> "DeclaredArtifactDigest":
        if self.verified:
            raise ValueError(
                "verified must remain False; Phase 40E reads no artifact bytes and "
                "cannot confirm a declared digest"
            )
        expected = DIGEST_HEX_LENGTHS[self.algorithm]
        if len(self.value) != expected:
            raise ValueError(
                f"{self.algorithm.value} digest must be {expected} hex characters, "
                f"got {len(self.value)}"
            )
        return self


# =========================================================================== #
# Migration provenance (pre-ingestion custody)
# =========================================================================== #
class MigrationProvenance(_MemoryMigrationModel):
    """Where migration material came from and how the user obtained it.

    A **dedicated pre-ingestion contract**, deliberately not
    :class:`~app.models.hive_models.ProvenanceChain`. That structure is a derived,
    advisory *graph* view — node/edge shaped, tolerant of partial derivation, and
    computed by ``app.services.provenance`` from records Hive|Mind already holds.
    Custody at the intake boundary is the opposite in every respect: it describes
    material Hive|Mind does **not** hold, it must be complete rather than
    partial, it is asserted rather than derived, and it is load-bearing for a
    trust decision. Reusing the graph contract would make an advisory structure
    into a security boundary and would leave custody with nowhere to live.

    ``source`` reuses :class:`~app.models.active_memory.MemorySource` because it
    is exactly the right shape — a typed identity with a bounded id and **no
    trust flag** (Phase 37A §5). Which source *types* are acceptable for intake
    is assessment policy, not contract shape.

    ``user_provided`` is pinned ``True`` and rejects being turned off. Hive|Mind
    claims no direct, account-to-account access to a provider's private system
    memory, so there is no legitimate intake path in which the material was not
    handed over by the user. Making that structural — rather than a convention —
    means no caller can declare machine-acquired material and have the contract
    accept it, even before the assessment refuses the corresponding custody kind.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    custody: MigrationCustodyKind
    source: MemorySource
    declared_origin_label: str | None = Field(
        default=None, max_length=MAX_MIGRATION_LABEL_LENGTH
    )
    declared_exported_at: datetime | None = None
    declared_acquired_at: datetime | None = None
    user_provided: bool = True
    verified: bool = False

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("declared_origin_label")
    @classmethod
    def _label_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "declared_origin_label")

    @field_validator("user_provided", "verified", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @model_validator(mode="after")
    def _validate_provenance(self) -> "MigrationProvenance":
        if not self.user_provided:
            raise ValueError(
                "user_provided must remain True; migration material is always "
                "handed over by the user, never acquired by Hive|Mind"
            )
        if self.verified:
            raise ValueError(
                "verified must remain False; Phase 40E confirms no custody claim"
            )
        return self


# =========================================================================== #
# Declared artifact descriptor
# =========================================================================== #
class MigrationArtifactDescriptor(_MemoryMigrationModel):
    """One artifact the user declares, described entirely from metadata.

    Every field is a *declaration*. Nothing here was measured: Phase 40E opens no
    file, lists no directory, and reads no byte, so ``declared_byte_size``,
    ``declared_entry_count``, ``entry_kind``, ``artifact_format`` and
    ``declared_digest`` are all claims about material the boundary has not seen.
    The ``declared_`` prefix is applied to every such field on purpose — a
    consumer reading this record must not be able to mistake a claim for a
    measurement.

    ``declared_byte_size`` and ``declared_digest`` are **optional in the
    contract** even though the intake policy requires both. Making absence
    representable is what lets the assessment report a typed
    ``missing_declared_size`` / ``missing_declared_digest`` diagnostic; a
    contract-mandatory field would surface the same condition as an untyped
    ``ValidationError`` with no diagnostic and no assessment record.

    Only *representability* is enforced here — bounds, non-emptiness, and
    hexadecimal digest shape. Path safety (absolute, traversing, control
    characters, reserved device names), entry-kind safety, format support, and
    size policy are decided by :mod:`app.services.memory_migration_intake` and
    reported as typed ``blocked``/``quarantined`` diagnostics.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    artifact_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    declared_relative_path: str = Field(
        min_length=1, max_length=MAX_MIGRATION_PATH_LENGTH
    )
    entry_kind: MigrationEntryKind
    artifact_format: MigrationArtifactFormat
    container: MigrationContainerKind
    declared_byte_size: int | None = Field(default=None, ge=0)
    declared_entry_count: int | None = Field(default=None, ge=0)
    declared_media_type: str | None = Field(
        default=None, max_length=MAX_MIGRATION_MEDIA_TYPE_LENGTH
    )
    declared_digest: DeclaredArtifactDigest | None = None
    declared_modified_at: datetime | None = None
    label: str | None = Field(default=None, max_length=MAX_MIGRATION_LABEL_LENGTH)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("artifact_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "artifact_id")

    @field_validator("declared_relative_path")
    @classmethod
    def _path_is_representable(cls, value: str) -> str:
        """Check only that the path can be recorded — never rewrite it.

        A declared path is **identity-bearing**: it is how a future parser will
        find the entry, how a candidate will trace back to its origin, and part of
        the artifact fingerprint. Stripping surrounding whitespace, collapsing
        separators, or normalizing case would silently change what the user
        declared and could make two materially different entries collide.

        So the value is preserved byte-for-byte, and only a path that cannot be
        recorded at all is rejected here. Everything a *safety* judgment would
        catch — leading or trailing whitespace, ``..`` traversal, an absolute
        root, a control character, a reserved device name — is left intact and
        reported as a typed diagnostic by the assessment.
        """

        if not value.strip():
            raise ValueError(
                "declared_relative_path must not be empty or whitespace-only"
            )
        return value

    @field_validator("declared_media_type", "label")
    @classmethod
    def _optional_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "optional text field")

    @field_validator("declared_byte_size", "declared_entry_count", mode="before")
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    def fingerprint(self) -> str:
        """This artifact's content-derived declaration fingerprint."""

        return derive_artifact_fingerprint(self)


def derive_artifact_fingerprint(descriptor: MigrationArtifactDescriptor) -> str:
    """Fold everything that materially defines a declared artifact into one id.

    ``artifact_id`` is deliberately **excluded**: the fingerprint answers "is this
    the same declared artifact?", and two entries describing identical material
    under two caller-assigned ids are a redundant declaration the assessment must
    be able to detect. Including the id would make every such pair look distinct
    and hide a double-import.

    ``label`` and ``metadata`` are also excluded: they are annotation, not
    identity, and folding them in would make a re-labelled declaration of the same
    bytes look like different material.
    """

    digest = descriptor.declared_digest
    material = [
        MEMORY_MIGRATION_CONTRACT_VERSION,
        descriptor.declared_relative_path,
        descriptor.entry_kind.value,
        descriptor.artifact_format.value,
        descriptor.container.value,
        descriptor.declared_byte_size,
        descriptor.declared_entry_count,
        descriptor.declared_media_type,
        None if digest is None else [digest.algorithm.value, digest.value],
        _canonical_datetime(descriptor.declared_modified_at),
    ]
    fingerprint = hashlib.sha256(_canonical_material(material)).hexdigest()
    return f"mm-artifact-{fingerprint[:_DIGEST_PREFIX_LENGTH]}"


# =========================================================================== #
# Declared bundle
# =========================================================================== #
class MemoryMigrationBundle(_MemoryMigrationModel):
    """The top-level intake declaration: custody plus a set of declared artifacts.

    A **passive declaration**, not memory and not evidence. ``is_memory`` and
    ``is_verified_evidence`` are pinned ``False`` and reject being turned on,
    which is the contract-level statement that raw migration material carries no
    standing whatsoever until it has been parsed (Phase 40F), reviewed, and
    persisted (Phase 40G). ``read_only`` is likewise pinned: constructing a bundle
    grants no write authority anywhere.

    ``intake_status`` is pinned to ``declared``. A caller cannot assert
    ``ready_for_parsing``; readiness is *derived* by the Phase 40E assessment from
    the bundle's actual contents. This is the migration-track form of the Phase
    40D rule that readiness is computed and never read off the record being
    checked — a bundle that could declare itself ready would make the whole
    boundary advisory.

    ``declared_artifact_count`` and ``declared_total_byte_size`` are optional
    caller claims that this contract **does not** reconcile against ``artifacts``.
    That is deliberate: a mismatch between what a bundle says it contains and what
    it actually carries is a meaningful intake finding, and the assessment
    recomputes both and reports the disagreement as a typed diagnostic. Enforcing
    consistency here would turn an informative finding into an untyped
    construction error.

    The one cross-field rule the contract *does* enforce is identifier
    uniqueness: duplicate ``artifact_id`` values would make every per-artifact
    diagnostic ambiguous about which entry it concerns, so the ambiguity is
    refused before any assessment runs.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    bundle_id: str = Field(min_length=1, max_length=MAX_MIGRATION_ID_LENGTH)
    label: str | None = Field(default=None, max_length=MAX_MIGRATION_LABEL_LENGTH)
    provenance: MigrationProvenance
    artifacts: list[MigrationArtifactDescriptor] = Field(
        default_factory=list, max_length=MAX_MIGRATION_BUNDLE_ARTIFACTS
    )
    declared_artifact_count: int | None = Field(default=None, ge=0)
    declared_total_byte_size: int | None = Field(default=None, ge=0)
    target_scope: MemoryScope | None = None
    declared_at: datetime | None = None
    intake_status: MigrationIntakeStatus = MigrationIntakeStatus.DECLARED
    metadata: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True
    is_memory: bool = False
    is_verified_evidence: bool = False

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator("bundle_id")
    @classmethod
    def _identifier_not_blank(cls, value: str) -> str:
        return _clean_required_text(value, "bundle_id")

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_required_text(value, "bundle label")

    @field_validator(
        "declared_artifact_count", "declared_total_byte_size", mode="before"
    )
    @classmethod
    def _counts_are_integers(cls, value: Any) -> Any:
        return _require_int(value)

    @field_validator("read_only", "is_memory", "is_verified_evidence", mode="before")
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @field_validator("metadata")
    @classmethod
    def _metadata_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_bounded_metadata(value)

    @model_validator(mode="after")
    def _validate_bundle(self) -> "MemoryMigrationBundle":
        if not self.read_only:
            raise ValueError("read_only must remain True")
        if self.is_memory:
            raise ValueError(
                "is_memory must remain False; a migration bundle is unparsed "
                "declared material, never memory"
            )
        if self.is_verified_evidence:
            raise ValueError(
                "is_verified_evidence must remain False; nothing in a migration "
                "bundle has been read, let alone verified"
            )
        if self.intake_status is not MigrationIntakeStatus.DECLARED:
            raise ValueError(
                f"intake_status must remain {MigrationIntakeStatus.DECLARED.value!r}; "
                "readiness is derived by the Phase 40E intake assessment, never "
                "declared by the caller"
            )

        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("artifacts contain duplicate artifact_id values")
        return self

    def normalized(self) -> "MemoryMigrationBundle":
        """Return a copy with ``artifacts`` deterministically ordered.

        Ordered by ``artifact_id``, which the model has already guaranteed is
        unique, so the result is byte-stable across runs and independent of
        insertion order. Mirrors ``SynthesisContextPacket.normalized()`` and
        ``RepositoryWorkspaceConfig.normalized()``.

        Ordering only — nothing is dropped, clipped, merged, or rewritten.
        """

        return self.model_copy(
            update={
                "artifacts": sorted(
                    self.artifacts, key=lambda artifact: artifact.artifact_id
                )
            }
        )

    def fingerprint(self) -> str:
        """This bundle's content-derived declaration fingerprint."""

        return derive_bundle_fingerprint(self)


def derive_bundle_fingerprint(bundle: MemoryMigrationBundle) -> str:
    """Fold everything that materially defines a declared bundle into one id.

    Artifact identifiers are paired with artifact fingerprints and folded in
    **sorted**, not declaration order: reordering the same declarations does not
    change the bundle, while renaming an artifact does. The identifier is the
    assessment's routing/provenance handle, so an old assessment must not
    authorize parsing a declaration whose handles changed even though
    :func:`derive_artifact_fingerprint` deliberately excludes them to detect
    redundant material.

    ``bundle_id`` remains excluded because it labels the bundle as a whole and is
    carried separately on the assessment. Artifact ids are different: downstream
    provenance routes individual parsed results through them, so changing one
    changes the declaration the parsing gate must authorize.

    The caller's declared count and total are included because the assessor
    reconciles them. Omitting assessment-driving fields would let a caller reuse a
    ready assessment after changing a declaration into one that should be blocked.
    """

    provenance = bundle.provenance
    material = [
        MEMORY_MIGRATION_CONTRACT_VERSION,
        provenance.custody.value,
        provenance.source.source_type.value,
        provenance.source.source_id,
        provenance.source.session_id,
        _canonical_datetime(provenance.declared_exported_at),
        _canonical_datetime(provenance.declared_acquired_at),
        None
        if bundle.target_scope is None
        else [bundle.target_scope.scope_type.value, bundle.target_scope.scope_id],
        _canonical_datetime(bundle.declared_at),
        bundle.declared_artifact_count,
        bundle.declared_total_byte_size,
        sorted(
            [item.artifact_id, derive_artifact_fingerprint(item)]
            for item in bundle.artifacts
        ),
    ]
    fingerprint = hashlib.sha256(_canonical_material(material)).hexdigest()
    return f"mm-bundle-{fingerprint[:_DIGEST_PREFIX_LENGTH]}"


# =========================================================================== #
# Candidate Memory policy
# =========================================================================== #
class CandidateMemoryPolicy(_MemoryMigrationModel):
    """The standing that migrated material may reach — pinned, not configurable.

    Phase 40E defines **no candidate record**: producing candidates requires
    parsing, which is Phase 40F. What it does define is the ceiling those
    candidates may never exceed, stated as a validated contract rather than as
    prose in a planning document so a later phase cannot quietly widen it.

    Every field is pinned and rejects any other value:

    * ``lifecycle_state`` is ``inactive`` — a candidate is never part of the
      active baseline, so the active-state calculation can never select one;
    * ``verification_state`` is ``unverified`` — imported material is not
      verified truth, and no amount of parsing makes it so;
    * ``represents_active_memory`` is ``False`` — a candidate cannot stand in for
      an approved Active Memory record anywhere it is read;
    * ``human_review_required`` is ``True`` — review is not optional;
    * ``persistable`` is ``False`` — Phase 40G is the exclusive reviewed-
      persistence boundary, and nothing before it may write a candidate anywhere.

    The two lifecycle/verification values reuse the stable Active Memory
    vocabularies rather than declaring migration-specific twins, so "inactive"
    and "unverified" mean exactly what they already mean everywhere else in the
    system. The permissive Active Memory *record* models are deliberately not
    reused: a ``MemoryRecord`` can be constructed as ``active`` and
    ``human_confirmed``, which is precisely the standing a migration candidate
    must be structurally incapable of holding.
    """

    schema_version: str = Field(default=MEMORY_MIGRATION_CONTRACT_VERSION)
    lifecycle_state: LifecycleState = LifecycleState.INACTIVE
    verification_state: VerificationState = VerificationState.UNVERIFIED
    represents_active_memory: bool = False
    human_review_required: bool = True
    persistable: bool = False

    @field_validator("schema_version")
    @classmethod
    def _version_supported(cls, value: str) -> str:
        return _validate_contract_version(value)

    @field_validator(
        "represents_active_memory",
        "human_review_required",
        "persistable",
        mode="before",
    )
    @classmethod
    def _flags_are_booleans(cls, value: Any) -> Any:
        return _require_bool(value)

    @model_validator(mode="after")
    def _policy_cannot_be_widened(self) -> "CandidateMemoryPolicy":
        if self.lifecycle_state is not LifecycleState.INACTIVE:
            raise ValueError(
                "candidate memory lifecycle_state must remain 'inactive'; a "
                "candidate is never part of the active baseline"
            )
        if self.verification_state is not VerificationState.UNVERIFIED:
            raise ValueError(
                "candidate memory verification_state must remain 'unverified'; "
                "imported material is never verified truth"
            )
        if self.represents_active_memory:
            raise ValueError(
                "represents_active_memory must remain False; a candidate cannot "
                "stand in for an approved Active Memory record"
            )
        if not self.human_review_required:
            raise ValueError("human_review_required must remain True")
        if self.persistable:
            raise ValueError(
                "persistable must remain False; Phase 40G is the exclusive "
                "reviewed-persistence boundary"
            )
        return self


CANDIDATE_MEMORY_POLICY = CandidateMemoryPolicy()
"""The single canonical candidate-memory ceiling for the migration track.

A module-level instance so Phase 40F and Phase 40G reference one object rather
than each constructing their own — two independently-built policies could drift,
and the whole point is that this one cannot be widened.
"""
