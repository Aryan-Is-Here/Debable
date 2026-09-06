"""Choosing the fact-check provider from configuration.

Two independent fallbacks, each degrading to something that needs no credentials:

* **Judgment** — Gemini when ``GEMINI_API_KEY`` is set, otherwise the deterministic stub.
* **Retrieval** — Tavily when ``TAVILY_API_KEY`` is set, otherwise Wikipedia, which needs no
  account at all.

So a fresh clone with an empty ``.env`` runs the entire debate flow, fact-check included; the
answers are simply fake. Adding a Gemini key makes them real, and adding a Tavily key widens
the evidence from Wikipedia to the whole trusted-source allowlist. Nothing else in the
application changes at any step, because everything downstream depends on the protocols in
``app/ai/base.py`` and ``app/search/base.py``.
"""

import logging
from functools import lru_cache

from app.ai.base import FactCheckProvider
from app.ai.gemini import GeminiFactCheckProvider
from app.ai.stub import StubFactCheckProvider
from app.core.config import Settings, get_settings
from app.search.base import SearchBackend
from app.search.tavily import TavilySearchBackend
from app.search.wikipedia import WikipediaSearchBackend

logger = logging.getLogger(__name__)


def build_search_backend(settings: Settings) -> SearchBackend:
    if settings.tavily_api_key:
        return TavilySearchBackend(
            api_key=settings.tavily_api_key,
            timeout_seconds=settings.fact_check_timeout_seconds,
        )
    return WikipediaSearchBackend(timeout_seconds=settings.fact_check_timeout_seconds)


def build_fact_check_provider(settings: Settings) -> FactCheckProvider:
    if not settings.fact_check_configured:
        logger.info("No Gemini key configured — fact-checks will return stub verdicts")
        return StubFactCheckProvider()

    return GeminiFactCheckProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        search=build_search_backend(settings),
        timeout_seconds=settings.fact_check_timeout_seconds,
    )


@lru_cache
def get_fact_check_provider() -> FactCheckProvider:
    """FastAPI dependency. Cached because the client holds a connection pool.

    Tests override this rather than setting keys, so nothing in the suite reaches a network.
    """
    return build_fact_check_provider(get_settings())
