"""What a search backend returns, and how it may fail."""

from dataclasses import dataclass
from typing import Protocol

from app.core.errors import ServiceUnavailableError

# How many results to hand the model. Enough for corroboration across sources, few enough
# that the prompt stays small — on a free tier the token budget is not the constraint, but
# a model given twenty half-relevant snippets reasons worse than one given four good ones.
DEFAULT_RESULT_LIMIT = 5


class SearchUnavailable(ServiceUnavailableError):
    """The search could not be performed.

    Distinct from "the search found nothing", which is an ordinary empty list and leads to an
    honest ``unverified`` verdict. This one means we never looked, and it must never be
    allowed to masquerade as a result — see ``app/ai/base.py``.
    """

    code = "search_unavailable"
    message = "Could not search for evidence right now. Try again shortly."


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One piece of evidence, with the URL a debater can click to check it themselves."""

    title: str
    url: str
    content: str


class SearchBackend(Protocol):
    """Finds evidence for a claim. Implementations must not retry internally.

    Retrying is the caller's decision because the caller knows the budget: on a free tier a
    silent retry doubles the cost of every transient failure.
    """

    async def search(self, query: str, *, limit: int = DEFAULT_RESULT_LIMIT) -> list[SearchResult]:
        """Return evidence for ``query``, or raise ``SearchUnavailable``.

        An empty list is a legitimate answer meaning "nothing found".
        """
        ...
