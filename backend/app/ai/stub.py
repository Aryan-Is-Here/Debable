"""A fact-check provider that never leaves the process.

This is what the whole test suite runs against, and it is not a convenience. The free
Gemini tier allows a small number of requests per day; a single ``pytest`` run against the
real API would spend the day's budget before anything had been demonstrated, and would make
the suite slow, flaky and dependent on a network. The existing 136 tests finish in under ten
seconds precisely because nothing in them talks to a third party.

It is also the provider used when no API key is configured, so the application runs — and
the debate room works end to end — on a fresh clone with no credentials at all.

Deterministic rather than random: a verdict that changes between runs cannot be asserted on.
"""

from app.ai.base import FactCheckProvider, ProviderResult, ProviderSource
from app.models.fact_check import FactCheckVerdict

_VERDICTS: tuple[FactCheckVerdict, ...] = (
    FactCheckVerdict.TRUE,
    FactCheckVerdict.FALSE,
    FactCheckVerdict.MISLEADING,
    FactCheckVerdict.UNVERIFIED,
)

_EXPLANATIONS: dict[FactCheckVerdict, str] = {
    FactCheckVerdict.TRUE: "Trusted sources corroborate this claim.",
    FactCheckVerdict.FALSE: "Trusted sources contradict this claim.",
    FactCheckVerdict.MISLEADING: "The claim contains a kernel of truth but omits key context.",
    FactCheckVerdict.UNVERIFIED: "No trusted source could confirm or refute this claim.",
}


class StubFactCheckProvider(FactCheckProvider):
    """Cycles a verdict from the claim's length. Mirrors the frontend's `mockFactCheck`."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def check(self, claim: str) -> ProviderResult:
        cleaned = claim.strip()
        # Recorded so tests can assert the claim — and *only* the claim — crossed the
        # boundary. Nothing about the room, the opponent or the transcript is sent.
        self.calls.append(cleaned)

        verdict = _VERDICTS[len(cleaned) % len(_VERDICTS)]
        return ProviderResult(
            verdict=verdict,
            explanation=_EXPLANATIONS[verdict],
            sources=[
                ProviderSource(
                    title="Example trusted source",
                    # On the allowlist, so the stub's results survive the trusted-source
                    # filter and tests exercise the same path as a real answer.
                    url="https://www.reuters.com/example-source",
                )
            ],
        )
