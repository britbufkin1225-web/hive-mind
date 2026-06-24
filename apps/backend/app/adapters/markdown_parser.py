"""Phase 6B — minimal, dependency-free markdown note parser.

Extracts the small normalized shape Hive|Mind needs from a single Obsidian
markdown note: title, frontmatter, tags, wiki links (``[[Note]]``) and markdown
links (``[text](url)``). Pure and filesystem-free — it operates on text that a
caller has already read. No third-party markdown/YAML dependency is used; a
tiny safe frontmatter parser covers the common scalar/list cases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# `---` fenced YAML frontmatter at the very start of a file.
_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
# First ATX heading line, e.g. "# Title".
_HEADING_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
# Inline tag like #project or #area/sub. Requires a word char immediately after
# `#`, so markdown headings ("# Heading") are not matched.
_INLINE_TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_][A-Za-z0-9_\-/]*)")
# Wiki link: [[Target]], [[Target|Alias]], [[Target#Heading]].
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
# Markdown link: [text](url). Also matches the link part of ![alt](url) images.
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass
class ParsedNote:
    """Normalized fields extracted from one markdown note."""

    title: str
    raw_content: str
    body: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    wiki_links: list[str] = field(default_factory=list)
    markdown_links: list[str] = field(default_factory=list)


def _clean_scalar(value: str) -> str:
    """Strip surrounding quotes and whitespace from a frontmatter scalar."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_scalar_or_inline_list(value: str) -> Any:
    """Parse a frontmatter value as an inline list ``[a, b]`` or a scalar."""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_clean_scalar(part) for part in inner.split(",") if part.strip()]
    return _clean_scalar(value)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse a tiny, safe subset of YAML frontmatter.

    Supports ``key: value`` scalars, inline lists ``key: [a, b]`` and block
    lists (``key:`` followed by ``- item`` lines). Anything more exotic is kept
    as a best-effort scalar string. Never raises.
    """
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") or stripped == "-":
            if current_key is not None:
                if not isinstance(result.get(current_key), list):
                    result[current_key] = []
                item = stripped[2:] if stripped.startswith("- ") else ""
                if item.strip():
                    result[current_key].append(_clean_scalar(item))
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        current_key = key
        result[key] = "" if value == "" else _parse_scalar_or_inline_list(value)
    return result


def _normalize_tags(value: Any) -> list[str]:
    """Normalize a frontmatter tags value into a clean ``#``-free list."""
    if isinstance(value, list):
        items = [str(item) for item in value]
    elif isinstance(value, str):
        items = re.split(r"[,\s]+", value.strip())
    else:
        items = []
    return [t.lstrip("#").strip() for t in items if t and t.strip()]


def _dedupe(items: list[str]) -> list[str]:
    """Order-preserving de-duplication."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    frontmatter = parse_frontmatter(match.group(1))
    body = text[match.end():]
    return frontmatter, body


def _extract_title(frontmatter: dict[str, Any], body: str, fallback: str) -> str:
    fm_title = frontmatter.get("title")
    if isinstance(fm_title, str) and fm_title.strip():
        return fm_title.strip()
    heading = _HEADING_RE.search(body)
    if heading:
        return heading.group(1).strip()
    return fallback


def _extract_wiki_links(body: str) -> list[str]:
    targets: list[str] = []
    for raw in _WIKILINK_RE.findall(body):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target:
            targets.append(target)
    return _dedupe(targets)


def parse_markdown(text: str, *, fallback_title: str) -> ParsedNote:
    """Parse one markdown note's text into the normalized :class:`ParsedNote`.

    ``fallback_title`` (typically the file stem) is used only when no
    frontmatter ``title`` and no leading heading are present.
    """
    frontmatter, body = _split_frontmatter(text)

    tags = _normalize_tags(frontmatter.get("tags", frontmatter.get("tag")))
    tags += [m for m in _INLINE_TAG_RE.findall(body)]

    return ParsedNote(
        title=_extract_title(frontmatter, body, fallback_title),
        raw_content=text,
        body=body,
        frontmatter=frontmatter,
        tags=_dedupe(tags),
        wiki_links=_extract_wiki_links(body),
        markdown_links=_dedupe(_MD_LINK_RE.findall(body)),
    )
