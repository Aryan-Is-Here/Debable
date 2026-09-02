"""The trusted-source filter.

This is the product's credibility boundary, and it is the one part of the fact-check that
runs on every result regardless of which provider answered — so it is worth testing harder
than its size suggests.
"""

import pytest

from app.core.sources import is_trusted_domain, is_trusted_source, source_domain


@pytest.mark.parametrize(
    "url",
    [
        "https://www.reuters.com/business/some-article",
        "https://apnews.com/article/123",
        "https://www.nature.com/articles/d41586",
        "https://www.bls.gov/ooh/",
        "https://who.int/news-room/fact-sheets",
    ],
)
def test_listed_domains_are_trusted(url: str) -> None:
    assert is_trusted_source(url)


@pytest.mark.parametrize(
    "url",
    [
        # Subdomains belong to their parent: the World Bank's data portal is the World Bank.
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        "https://ourworldindata.org.cdn.who.int/x",
        "https://www.ons.gov.uk/economy",
    ],
)
def test_subdomains_of_listed_domains_are_trusted(url: str) -> None:
    assert is_trusted_source(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.whitehouse.gov/briefing",
        "https://web.mit.edu/paper",
        "https://www.cam.ac.uk/research",
        "https://data.gov.uk/dataset",
    ],
)
def test_government_and_academic_suffixes_are_trusted(url: str) -> None:
    """Enumerating every .gov and .edu would guarantee a stale list; the suffix is the point."""
    assert is_trusted_source(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://someblog.example.com/post",
        "https://medium.com/@someone/why-i-am-right",
        "https://en.wikipedia.org/wiki/Fact",
    ],
)
def test_unlisted_domains_are_not_trusted(url: str) -> None:
    assert not is_trusted_source(url)


@pytest.mark.parametrize(
    "url",
    [
        # The attack the segment-boundary check exists to stop: a trusted name appearing as
        # a prefix of a domain somebody else controls.
        "https://reuters.com.evil.example/article",
        "https://notreuters.com/article",
        "https://fakewho.int.attacker.net/page",
        "https://bls.gov.phishing.io/data",
    ],
)
def test_a_trusted_name_inside_another_domain_is_not_trusted(url: str) -> None:
    assert not is_trusted_source(url)


@pytest.mark.parametrize(
    "url",
    [
        "not a url",
        "",
        "ftp://reuters.com/file",
        # A citation nobody can click is not a citation.
        "javascript:alert(1)",
        "file:///etc/passwd",
        "//reuters.com/protocol-relative",
    ],
)
def test_unusable_urls_are_not_trusted(url: str) -> None:
    assert not is_trusted_source(url)


def test_source_domain_strips_www_and_lowercases() -> None:
    assert source_domain("https://WWW.Reuters.COM/x") == "reuters.com"


def test_source_domain_returns_none_for_a_non_url() -> None:
    assert source_domain("reuters.com") is None


# --- Bare-hostname checks --------------------------------------------------------------
#
# Gemini hands back every citation's URI as a vertexaisearch.cloud.google.com redirect and
# puts the real publisher in a separate `domain` field, so the hostname path is the one the
# provider actually exercises.


@pytest.mark.parametrize(
    "host",
    ["reuters.com", "www.reuters.com", "REUTERS.COM", "data.worldbank.org", "nasa.gov"],
)
def test_trusted_hostnames_pass(host: str) -> None:
    assert is_trusted_domain(host)


@pytest.mark.parametrize("host", ["example.com", "reuters.com.evil.example", "", None])
def test_untrusted_hostnames_fail(host: str | None) -> None:
    assert not is_trusted_domain(host)


def test_the_redirect_host_itself_is_not_trusted() -> None:
    """Filtering on the URI instead of the domain field would let every citation through."""
    assert not is_trusted_domain("vertexaisearch.cloud.google.com")
