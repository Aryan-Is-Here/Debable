"""Search backends, against recorded payloads rather than the live services.

Nothing here makes a network call. That is deliberate and load-bearing: the Tavily free tier
is 1,000 searches a month, and a suite that spent one per run would exhaust it in a fortnight
of ordinary development.

The payload shapes below were taken from real responses during development.
"""

import httpx
import pytest

from app.core.sources import TRUSTED_SOURCE_DOMAINS
from app.search.base import SearchUnavailable
from app.search.tavily import TavilySearchBackend
from app.search.wikipedia import WikipediaSearchBackend

WIKIPEDIA_PAYLOAD = {
    "query": {
        "pages": [
            {
                "pageid": 1,
                "title": "Wall Street crash of 1929",
                "fullurl": "https://en.wikipedia.org/wiki/Wall_Street_crash_of_1929",
                "extract": "The Wall Street crash of 1929 was a major stock market crash.",
            },
            {
                "pageid": 2,
                "title": "Great Depression",
                "fullurl": "https://en.wikipedia.org/wiki/Great_Depression",
                "extract": "The Great Depression was a severe worldwide economic downturn.",
            },
        ]
    }
}

TAVILY_PAYLOAD = {
    "results": [
        {
            "title": "Labor Force Statistics",
            "url": "https://www.bls.gov/cps/",
            "content": "The unemployment rate averaged 3.6 percent in 2023.",
            "score": 0.98,
        }
    ]
}


def _client_factory(handler):
    """Patch httpx.AsyncClient so the backend talks to a transport we control."""
    transport = httpx.MockTransport(handler)

    class _Patched(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return _Patched


# --- Wikipedia --------------------------------------------------------------------------


async def test_wikipedia_returns_titles_urls_and_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=WIKIPEDIA_PAYLOAD)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))

    results = await WikipediaSearchBackend().search("the great depression")

    assert [r.title for r in results] == ["Wall Street crash of 1929", "Great Depression"]
    assert results[0].url.startswith("https://en.wikipedia.org/wiki/")
    assert "stock market crash" in results[0].content


async def test_wikipedia_identifies_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wikimedia enforces its User-Agent policy — a generic agent gets a 403."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, json=WIKIPEDIA_PAYLOAD)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    await WikipediaSearchBackend().search("anything")

    assert "Debable" in seen["ua"]
    # A contact route, which is what the policy actually requires.
    assert "github.com" in seen["ua"]


async def test_wikipedia_with_no_matches_returns_an_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ "Found nothing" is an ordinary answer, not a failure — it becomes `unverified`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"batchcomplete": True})

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))

    assert await WikipediaSearchBackend().search("zzzzz") == []


async def test_wikipedia_skips_pages_with_no_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "query": {
            "pages": [
                {"title": "Redirect", "fullurl": "https://en.wikipedia.org/wiki/R", "extract": ""},
                {
                    "title": "Real",
                    "fullurl": "https://en.wikipedia.org/wiki/Real",
                    "extract": "Content.",
                },
            ]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    results = await WikipediaSearchBackend().search("x")

    assert [r.title for r in results] == ["Real"]


async def test_wikipedia_failure_raises_rather_than_returning_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty list would masquerade as `unverified`; a raise cannot be mistaken for one."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Please respect our robot policy")

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))

    with pytest.raises(SearchUnavailable):
        await WikipediaSearchBackend().search("x")


# --- Tavily -----------------------------------------------------------------------------


async def test_tavily_restricts_search_to_the_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole reason for using Tavily: the allowlist constrains retrieval, not citations."""
    import json

    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json=TAVILY_PAYLOAD)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    await TavilySearchBackend(api_key="test-key").search("unemployment 2023")

    assert seen["include_domains_mode"] == "filter"
    assert set(seen["include_domains"]) == set(TRUSTED_SOURCE_DOMAINS)  # type: ignore[arg-type]
    # "advanced" costs two credits of a thousand-a-month budget for relevance we do not need.
    assert seen["search_depth"] == "basic"
    assert seen["auth"] == "Bearer test-key"


async def test_tavily_maps_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=TAVILY_PAYLOAD)

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))
    results = await TavilySearchBackend(api_key="k").search("x")

    assert len(results) == 1
    assert results[0].url == "https://www.bls.gov/cps/"
    assert "3.6 percent" in results[0].content


async def test_an_exhausted_tavily_allowance_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "quota exceeded"})

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory(handler))

    with pytest.raises(SearchUnavailable):
        await TavilySearchBackend(api_key="k").search("x")
