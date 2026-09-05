"""Evidence retrieval for the fact-check.

The fact-check does its own searching rather than letting the model search, because free-tier
Google Search grounding turned out to be unobtainable (see ``app/ai/gemini.py``). That forced
change is an improvement: when we run the search, the trusted-source allowlist becomes a
constraint on *retrieval* rather than a filter on citations, so an untrusted page is never
read at all.

Two backends, following the same shape as ``app/ai/``: the better one when a key is present,
a free one that needs no credentials when it is not.
"""

from app.search.base import SearchBackend, SearchResult, SearchUnavailable

__all__ = ["SearchBackend", "SearchResult", "SearchUnavailable"]
