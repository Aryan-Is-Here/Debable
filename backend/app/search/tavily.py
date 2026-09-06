"""Tavily search — the backend that makes the allowlist a retrieval constraint.

``include_domains`` with ``include_domains_mode="filter"`` restricts results to the listed
domains only, up to 300. That is the strongest form of this product's credibility guarantee:
an untrusted page is never fetched, so the model cannot reason from one and then be caught by
a citation filter afterwards. Both earlier designs — Anthropic's web search and Gemini's
grounding — offered something weaker or nothing at all.

Free tier is 1,000 searches a month with no credit card. ``search_depth="basic"`` costs one
credit; ``"advanced"`` costs two and is not worth double the budget here.
"""

import logging

import httpx

from app.core.sources import TRUSTED_SOURCE_DOMAINS
from app.search.base import DEFAULT_RESULT_LIMIT, SearchBackend, SearchResult, SearchUnavailable

logger = logging.getLogger(__name__)

API_URL = "https://api.tavily.com/search"

# Tavily accepts up to 300 entries. The bare domains from the allowlist; the `.gov`/`.edu`
# suffix rules in `sources.py` have no equivalent here, so results from those are reached
# only if their specific domain is listed. The post-filter in the service layer still runs,
# which keeps the two backends behaving identically from the caller's point of view.
_INCLUDE_DOMAINS = list(TRUSTED_SOURCE_DOMAINS)


class TavilySearchBackend(SearchBackend):
    """Searches the web, restricted to the trusted-source allowlist."""

    def __init__(self, *, api_key: str, timeout_seconds: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def search(self, query: str, *, limit: int = DEFAULT_RESULT_LIMIT) -> list[SearchResult]:
        body = {
            "query": query,
            "max_results": limit,
            # One credit per search. "advanced" doubles the cost for relevance we do not need.
            "search_depth": "basic",
            "include_domains": _INCLUDE_DOMAINS,
            # "filter" restricts to these domains; "boost" would merely prefer them, which
            # is not a guarantee and would silently weaken the whole point of the allowlist.
            "include_domains_mode": "filter",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    API_URL,
                    json=body,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 - transport, status and JSON failures alike
            # Includes a 432/429 for an exhausted monthly allowance. Either way the claim was
            # not checked, and that must not be recorded as a verdict.
            logger.warning("Tavily search failed", exc_info=exc)
            raise SearchUnavailable() from exc

        return _to_results(payload)


def _to_results(payload: object) -> list[SearchResult]:
    """Map Tavily's response. An empty ``results`` list means nothing was found, not an error."""
    if not isinstance(payload, dict):
        raise SearchUnavailable("The search service returned an unexpected response.")

    results: list[SearchResult] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        content = (item.get("content") or "").strip()
        if not url or not title or not content:
            continue
        results.append(SearchResult(title=title, url=url, content=content))
    return results
