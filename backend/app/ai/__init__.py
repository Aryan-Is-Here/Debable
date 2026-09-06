"""The AI fact-check client.

``docs/03-system-architecture.md`` draws the AI as its own box, and the property that box
exists to guarantee is that **the AI never listens continuously and only the submitted claim
crosses the boundary**. An HTTP client satisfies that; a separate deployable would add
operations work without adding isolation, so this package is a client.

Everything here is behind ``FactCheckProvider`` so the rest of the application never learns
which model answered. That is not speculative generality — the project has no budget, the
provider is whichever free tier is currently viable, and it has already changed once
(Anthropic to Gemini) before a line of the service layer was written.
"""

from app.ai.base import (
    FactCheckProvider,
    FactCheckUnavailable,
    ProviderResult,
    ProviderSource,
)

__all__ = [
    "FactCheckProvider",
    "FactCheckUnavailable",
    "ProviderResult",
    "ProviderSource",
]
