"""Wikipedia search — the backend that needs no account, no key and no card.

This is what runs before a Tavily key is configured, so the fact-check works on a fresh
clone. It is narrower than a web search: Wikipedia covers most claims a debate actually turns
on — statistics, history, definitions — and cites its own primary sources, but it cannot
reach a BLS table directly, so expect more honest ``unverified`` verdicts than Tavily gives.

Two API details that are not optional:

* **The User-Agent must identify the application and a contact.** Wikimedia's robot policy is
  enforced, not advisory — a generic agent gets a ``403`` with a link to the policy, which is
  exactly what happened the first time this was tried.
* ``generator=search`` combined with ``prop=extracts`` does search and text retrieval in **one**
  request, and ``exintro`` works alongside ``exlimit=max`` despite what the parameter docs
  imply. Verified against the live API.
"""

import logging

import httpx

from app.search.base import DEFAULT_RESULT_LIMIT, SearchBackend, SearchResult, SearchUnavailable

logger = logging.getLogger(__name__)

API_URL = "https://en.wikipedia.org/w/api.php"

# Wikimedia requires a descriptive agent with a way to make contact. See
# https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
USER_AGENT = "Debable/0.1 (https://github.com/Aryan-Is-Here/Debable; educational project) httpx"


class WikipediaSearchBackend(SearchBackend):
    """Searches English Wikipedia and returns each article's introduction."""

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout = timeout_seconds

    async def search(self, query: str, *, limit: int = DEFAULT_RESULT_LIMIT) -> list[SearchResult]:
        params = {
            "action": "query",
            "format": "json",
            # Objects as a list rather than a dict keyed by page id — much easier to read.
            "formatversion": "2",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": str(limit),
            # Articles only: no talk pages, no user pages.
            "gsrnamespace": "0",
            "prop": "extracts|info",
            "inprop": "url",
            "explaintext": "1",
            "exintro": "1",
            "exlimit": "max",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    API_URL,
                    params=params,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 - transport, status and JSON failures alike
            logger.warning("Wikipedia search failed", exc_info=exc)
            raise SearchUnavailable() from exc

        return _to_results(payload)


def _to_results(payload: object) -> list[SearchResult]:
    """Pull usable results out of a MediaWiki response.

    Tolerant on purpose: a missing ``query`` key means the search matched nothing, which is an
    empty list rather than an error, and a page whose extract came back blank is simply not
    evidence.
    """
    if not isinstance(payload, dict):
        raise SearchUnavailable("The search service returned an unexpected response.")

    pages = payload.get("query", {}).get("pages", []) if payload.get("query") else []

    results: list[SearchResult] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        extract = (page.get("extract") or "").strip()
        url = page.get("fullurl")
        title = page.get("title")
        if not extract or not url or not title:
            continue
        results.append(SearchResult(title=title, url=url, content=extract))
    return results
