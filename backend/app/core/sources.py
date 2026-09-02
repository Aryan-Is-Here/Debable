"""The trusted sources a fact-check may cite.

This list is the product's credibility boundary. A verdict is only ever shown to debaters
when at least one citation comes from a domain here; if nothing on this list supports the
claim, the verdict is ``unverified`` rather than a guess with a plausible-looking link.

**Why the filtering happens here rather than at the search API.** The original design put
the allowlist on the search tool itself, so untrusted pages were never retrieved at all.
Gemini's free Google Search grounding supports only ``exclude_domains`` — there is no
include-list outside paid Vertex tiers — so the boundary moved to *after* retrieval.

The honest consequence: the model may have **read** a page that is not on this list, and
reasoned from it. What this list guarantees is narrower than it was — it governs what can be
*cited*, not what can be *read*. That is why an answer with no surviving citation is
downgraded to ``unverified`` instead of being shown with whatever sources came back: a
verdict the debaters cannot check is worse than no verdict.

If the project ever moves to a paid tier or a self-hosted search index, push this list back
down to the retrieval call and delete the post-filter — the guarantee gets stronger for free.
"""

from typing import Final
from urllib.parse import urlsplit

# Wire services, official statistics, public health bodies, and primary science. Chosen to
# be checkable by a debater in one click, not to be exhaustive — a source nobody recognises
# does not settle an argument even when it is correct.
TRUSTED_SOURCE_DOMAINS: Final[tuple[str, ...]] = (
    # Wire services and reference reporting
    "reuters.com",
    "apnews.com",
    "bbc.co.uk",
    "bbc.com",
    "npr.org",
    "pbs.org",
    # Primary science
    "nature.com",
    "science.org",
    "thelancet.com",
    "nejm.org",
    "bmj.com",
    "pnas.org",
    "arxiv.org",
    # Public health
    "who.int",
    "cdc.gov",
    "nih.gov",
    "nhs.uk",
    # Official statistics and government
    "bls.gov",
    "census.gov",
    "cbo.gov",
    "gao.gov",
    "federalreserve.gov",
    "ons.gov.uk",
    "europa.eu",
    # Multilateral bodies
    "worldbank.org",
    "imf.org",
    "oecd.org",
    "un.org",
    "iea.org",
    "ipcc.ch",
)

# Suffixes accepted wholesale. Government and academic domains are numerous enough that
# enumerating them would guarantee an out-of-date list, and their provenance is the point.
TRUSTED_SOURCE_SUFFIXES: Final[tuple[str, ...]] = (
    ".gov",
    ".edu",
    ".ac.uk",
    ".gov.uk",
    ".int",
)


def source_domain(url: str) -> str | None:
    """The bare hostname of ``url``, lowercased and without ``www.``.

    Returns ``None`` for anything that is not an absolute http(s) URL — a citation the
    debaters cannot click is not a citation.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    host = parts.hostname.lower()
    return host.removeprefix("www.")


def is_trusted_source(url: str) -> bool:
    """Whether a citation URL may be shown to debaters.

    Subdomains count: ``data.worldbank.org`` is the World Bank. The check is on the
    hostname's segment boundary rather than a substring, so ``reuters.com.example.net``
    does not pass by containing a trusted name.
    """
    host = source_domain(url)
    if host is None:
        return False
    if any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_SOURCE_DOMAINS):
        return True
    return any(host.endswith(suffix) for suffix in TRUSTED_SOURCE_SUFFIXES)
