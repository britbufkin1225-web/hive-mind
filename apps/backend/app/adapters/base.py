"""Future source adapter interface (Phase 6A).

Defines the conceptual contract every source adapter will implement:

    adapter config in -> normalized document candidates out

This is a contract placeholder. No concrete adapter in this phase loads data,
traverses the filesystem, or parses content; `discover()` is abstract and
concrete adapters raise NotImplementedError until a future import phase.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from pydantic import BaseModel


class SourceAdapter(ABC):
    """Abstract base for future source adapters.

    A concrete adapter receives its configuration at construction time and
    yields normalized `*DocumentCandidate` models from `discover()`. Phase 6A
    defines the interface only — nothing here reads a real source.
    """

    @abstractmethod
    def discover(self) -> Iterable[BaseModel]:
        """Yield normalized document candidates for this source.

        Not implemented in Phase 6A. Concrete adapters raise
        NotImplementedError until a future phase implements real loading.
        """
        raise NotImplementedError
