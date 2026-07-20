"""Phase 39B - reusable path and remote normalization helpers.

This is the small, dependency-light maintainability seam for repository
workspace configuration. It centralizes the identity-comparison rules so the
contract model, configuration service, and operator tooling all agree on when
two repository roots (or two remotes) are "the same".

Import-time dependencies are standard-library only. The authoritative Git remote
normalization and credential-detection helpers already live in
``app.services.repository_git_adapter``; the remote helpers here reuse the
adapter's normalization through a deferred import so a single source of truth is
preserved without creating an import cycle with the contract model.
"""

from __future__ import annotations

import re
import unicodedata

# Collapses runs of two or more forward slashes into one. A leading UNC pair is
# restored by the caller so ``//server/share`` keeps its network-root meaning.
_MULTISLASH_RE = re.compile(r"/{2,}")

# Matches ``scheme://userinfo@`` at the start of a URL. Used to decide whether a
# remote embeds credentials. The scp-like ``git@host:path`` SSH form has no
# ``://`` and therefore never matches here.
_SCHEME_USERINFO_RE = re.compile(
    r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://(?P<userinfo>[^/@\s]+)@"
)


def display_repository_root(path: str) -> str:
    """Return the operator-readable repository root (NFC-normalized, trimmed).

    The original separators and casing are preserved so the value stays readable
    to a human. Only Unicode form and surrounding whitespace are normalized.
    """

    return unicodedata.normalize("NFC", path).strip()


def repository_root_comparison_key(path: str) -> str:
    """Return a canonical, case-insensitive key for duplicate-root detection.

    The key folds the platform-insensitive aspects of a Windows-first path:
    Unicode form (NFC), separator direction (``\\`` -> ``/``), duplicate
    separators, trailing separators, drive-letter casing, and general case. Two
    operator-supplied paths that name the same location collapse to one key while
    the display form (see :func:`display_repository_root`) stays intact. The path
    does not need to exist; this is a pure string transformation.
    """

    text = unicodedata.normalize("NFC", path).strip()
    text = text.replace("\\", "/")
    is_unc = text.startswith("//")
    text = _MULTISLASH_RE.sub("/", text)
    if is_unc:
        text = "/" + text
    if len(text) > 1:
        stripped = text.rstrip("/")
        text = stripped if stripped else "/"
    return text.casefold()


def normalize_remote(remote: str) -> str:
    """Return the adapter-consistent normalized form of a Git remote URL.

    Delegates to the authoritative
    :func:`app.services.repository_git_adapter._normalize_remote_url` so an
    expected remote recorded here compares equal to an observed remote produced
    by the read-only Git adapter.
    """

    from app.services.repository_git_adapter import _normalize_remote_url

    return _normalize_remote_url(remote)


def remote_has_credentials(remote: str) -> bool:
    """Return whether a remote URL embeds credentials or an access token.

    The canonical SSH forms ``git@host:path`` (scp-like) and ``ssh://git@host/``
    are treated as safe identity, not secrets. Any ``user:secret@`` userinfo, or a
    lone non-``git`` userinfo on a network scheme (a likely token), is rejected.
    """

    text = remote.strip()
    match = _SCHEME_USERINFO_RE.match(text)
    if match is None:
        return False
    userinfo = match.group("userinfo")
    scheme = match.group("scheme").lower()
    if ":" in userinfo:
        return True
    if scheme == "ssh" and userinfo.lower() == "git":
        return False
    return True


def redact_remote(remote: str) -> str:
    """Return a remote with any embedded credentials removed for safe display."""

    from app.services.repository_git_adapter import _redact_credentials

    return _redact_credentials(remote)
