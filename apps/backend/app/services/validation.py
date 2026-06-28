"""Phase 18E — backend request-shape defensive validation helpers.

Phase 18B closed the *field-level* request edges (type, length, presence, blank,
enum) at trust boundary #1 (request -> API). Phase 18D triaged the remaining
*structural* edges and named deeply nested / recursive request bodies as the
highest-value deferred item (Medium risk).

This module implements that one guard: a bounded nesting-depth check for
free-form request structures. It is intentionally:

* **Pure and dependency-free** — no Pydantic / FastAPI imports, so it is unit
  testable in isolation and can be reused by any model that accepts a free-form
  ``dict[str, Any]`` / nested structure.
* **Iterative, never recursive** — the very input this guards against is a
  deeply nested object (``{"a": {"a": {"a": ...}}}``). A recursive depth check
  would itself overflow the Python stack on that input. The traversal below uses
  an explicit stack and short-circuits the moment the bound is exceeded, so it
  stays cheap and safe even on a hostile payload.
* **Additive and bound by a named constant** — realistic request bodies nest a
  handful of levels deep (an import body wraps lists of records whose
  ``metadata`` dicts are shallow); the limit is far above any legitimate value,
  so no existing valid request regresses.

The guard raises a plain :class:`ValueError`. Pydantic turns that into the same
structured ``422`` the existing Phase 18B field validators produce, keeping the
error-response contract consistent (Phase 18D "Error Response Safety"). The
message is generic and leaks no traceback, internal field, or filesystem path.
"""

from typing import Any

# --------------------------------------------------------------------------- #
# Maximum nesting depth for a free-form request structure.
#
# "Depth" counts nested containers (dict/list): the top-level body is depth 1,
# a value one level inside it is depth 2, and so on. Legitimate Hive|Mind bodies
# are shallow — the deepest is the snapshot import (request -> list -> record ->
# metadata dict -> a small handful of nested values), comfortably in single
# digits. 32 leaves generous headroom for any realistic ``metadata`` payload
# while still rejecting the pathological, recursion-shaped inputs Phase 18D
# flagged. The value is deliberately a single constant so the bound is auditable
# and the same on every guarded model.
# --------------------------------------------------------------------------- #
MAX_REQUEST_NESTING_DEPTH = 32


def assert_within_nesting_depth(
    value: Any, max_depth: int = MAX_REQUEST_NESTING_DEPTH
) -> None:
    """Raise ``ValueError`` if ``value`` nests containers deeper than ``max_depth``.

    Only ``dict`` and ``list`` containers contribute to depth; scalars never do.
    The traversal is iterative and short-circuits on the first over-depth
    container, so it never recurses and never visits more of a hostile payload
    than necessary to reject it.
    """
    # Each stack item is (container, depth_of_that_container). The top-level
    # value sits at depth 1.
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(
                "Request body is too deeply nested "
                f"(maximum nesting depth is {max_depth})"
            )
        if isinstance(node, dict):
            children: Any = node.values()
        elif isinstance(node, list):
            children = node
        else:
            continue
        for child in children:
            if isinstance(child, (dict, list)):
                stack.append((child, depth + 1))
