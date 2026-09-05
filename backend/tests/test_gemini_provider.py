"""The Gemini provider's mapping and failure handling, without calling Gemini.

Only ``_judge`` talks to the model, so these tests drive a provider whose ``_judge`` is
replaced. What is being checked is the part that decides what gets persisted: whether a
citation can be invented, and whether a failure can be mistaken for a verdict.
"""

import pytest

from app.ai.base import FactCheckUnavailable
from app.ai.gemini import GeminiFactCheckProvider, _build_prompt, _to_provider_result
from app.models.fact_check import FactCheckVerdict
from app.search.base import SearchBackend, SearchResult, SearchUnavailable

RESULTS = [
    SearchResult(
        title="Wall Street crash of 1929",
        url="https://en.wikipedia.org/wiki/Wall_Street_crash_of_1929",
        content="The crash began in October 1929.",
    ),
    SearchResult(
        title="Great Depression",
        url="https://en.wikipedia.org/wiki/Great_Depression",
        content="A severe worldwide economic downturn.",
    ),
]


class FakeSearch(SearchBackend):
    def __init__(self, results=None, error=None):
        self.results = results if results is not None else []
        self.error = error
        self.queries: list[str] = []

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.results


def _provider(search: SearchBackend, payload: dict | Exception | None = None):
    """A provider whose model call is replaced by a scripted payload."""
    provider = GeminiFactCheckProvider.__new__(GeminiFactCheckProvider)
    provider._search = search  # type: ignore[attr-defined]
    provider._model = "test"  # type: ignore[attr-defined]
    provider._timeout = 5.0  # type: ignore[attr-defined]

    async def judge(claim, results):
        if isinstance(payload, Exception):
            raise payload
        assert payload is not None
        return payload

    provider._judge = judge  # type: ignore[attr-defined]
    return provider


# --- Mapping ----------------------------------------------------------------------------


async def test_cited_indices_resolve_to_the_supplied_sources() -> None:
    provider = _provider(
        FakeSearch(RESULTS),
        {"verdict": "true", "explanation": "Backed up.", "source_indices": [1, 2]},
    )

    result = await provider.check("The crash was in 1929.")

    assert result.verdict == FactCheckVerdict.TRUE
    assert [s.title for s in result.sources] == [
        "Wall Street crash of 1929",
        "Great Depression",
    ]


async def test_an_out_of_range_index_is_discarded_not_invented() -> None:
    """The mechanism that makes a hallucinated citation impossible rather than unlikely."""
    provider = _provider(
        FakeSearch(RESULTS),
        {"verdict": "true", "explanation": "x", "source_indices": [1, 7, 99, 0, -3]},
    )

    result = await provider.check("A claim about history.")

    assert [s.title for s in result.sources] == ["Wall Street crash of 1929"]


async def test_duplicate_indices_are_collapsed() -> None:
    provider = _provider(
        FakeSearch(RESULTS),
        {"verdict": "false", "explanation": "x", "source_indices": [2, 2, 2]},
    )

    result = await provider.check("A claim about history.")

    assert len(result.sources) == 1


async def test_no_search_results_gives_an_honest_unverified() -> None:
    """Checked, found nothing. This is the one place an empty answer is a real verdict."""
    search = FakeSearch([])
    provider = _provider(search, {"verdict": "true", "explanation": "unused"})

    result = await provider.check("Something nobody has written about.")

    assert result.verdict == FactCheckVerdict.UNVERIFIED
    assert result.sources == []
    # The model is never asked, so no request is spent on a claim with no evidence.
    assert search.queries == ["Something nobody has written about."]


async def test_a_search_failure_propagates_rather_than_becoming_a_verdict() -> None:
    provider = _provider(FakeSearch(error=SearchUnavailable()), {"verdict": "true"})

    with pytest.raises(SearchUnavailable):
        await provider.check("A claim.")


async def test_a_model_failure_propagates() -> None:
    provider = _provider(FakeSearch(RESULTS), FactCheckUnavailable())

    with pytest.raises(FactCheckUnavailable):
        await provider.check("A claim.")


async def test_an_unknown_verdict_raises_rather_than_being_guessed() -> None:
    provider = _provider(
        FakeSearch(RESULTS),
        {"verdict": "probably-ish", "explanation": "x", "source_indices": [1]},
    )

    with pytest.raises(FactCheckUnavailable):
        await provider.check("A claim.")


def test_a_missing_explanation_does_not_discard_the_verdict() -> None:
    """The verdict is the load-bearing part; a missing sentence is a cosmetic loss."""
    result = _to_provider_result({"verdict": "misleading", "source_indices": [1]}, RESULTS)

    assert result.verdict == FactCheckVerdict.MISLEADING
    assert result.explanation


# --- Prompt -----------------------------------------------------------------------------


def test_sources_are_numbered_from_one() -> None:
    """The model cites by index, so the numbering has to match what `_to_provider_result` reads."""
    prompt = _build_prompt("Some claim.", RESULTS)

    assert "[1] Wall Street crash of 1929" in prompt
    assert "[2] Great Depression" in prompt
    assert "Some claim." in prompt


def test_long_sources_are_truncated() -> None:
    """One long article must not crowd the others out of the prompt."""
    long_results = [SearchResult(title="Long", url="https://example.org", content="x" * 5000)]

    prompt = _build_prompt("Claim.", long_results)

    assert len(prompt) < 3000
