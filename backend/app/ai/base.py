"""What a fact-check provider must return, and how it may fail.

The distinction this module exists to enforce:

* ``UNVERIFIED`` is a **verdict**. It means the claim was checked and no trusted source
  confirmed or refuted it. That is a real, informative answer.
* ``FactCheckUnavailable`` is an **error**. It means the claim was never checked — the quota
  ran out, the network failed, the model returned nonsense.

Collapsing the second into the first would be the most damaging bug this phase could ship.
The whole project exists to answer whether AI fact-checking improves debates; if failed
requests are silently recorded as "unverified", the dataset fills with claims that were
never examined and are indistinguishable from claims that were. An error is visible and
retryable. A false ``unverified`` is neither, and it is *persisted*.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.core.errors import ServiceUnavailableError
from app.models.fact_check import FactCheckVerdict


class FactCheckUnavailable(ServiceUnavailableError):
    """The claim could not be checked — as distinct from checked and unresolved.

    A ``ServiceUnavailableError`` subclass so it already carries a 503 and the standard
    error envelope; nothing is persisted when this is raised.
    """

    code = "fact_check_unavailable"
    message = "The fact-check service is unavailable. Try again shortly."


@dataclass(frozen=True, slots=True)
class ProviderSource:
    """One citation. Mirrors ``FactCheckSource`` in ``frontend/lib/types.ts``."""

    title: str
    url: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """A provider's answer, before the trusted-source filter is applied.

    Sources are unfiltered here on purpose: the provider's job is to report faithfully what
    it found, and the decision about what may be *shown* belongs to the service layer, in
    one place, where it can be tested without a model.
    """

    verdict: FactCheckVerdict
    explanation: str
    sources: list[ProviderSource] = field(default_factory=list)


class FactCheckProvider(Protocol):
    """Checks one claim. Implementations must not retry internally.

    Retrying is the caller's decision because the caller knows the budget: on a free tier a
    silent retry inside the provider can double the cost of every transient failure and
    exhaust a daily quota without anything in the logs explaining why.
    """

    async def check(self, claim: str) -> ProviderResult:
        """Evaluate ``claim``, or raise ``FactCheckUnavailable`` if it cannot be evaluated."""
        ...
