"""Gemini fact-check provider.

**Why Gemini 2.5 Flash and not something newer.** It is the only model whose Google Search
grounding is free of charge (500 grounded requests/day). Every Gemini 3.x model lists
grounding as unavailable on the free tier. The project has no budget, so the model is a
constraint, not a preference.

**Why the response is parsed from text rather than a JSON schema.** Gemini only supports
structured output *together with* the search tool from 3.x onwards; on 2.5 the pair is
rejected with a 400, and the documented workaround — one grounded call to research, a second
unrounded call to reformat — doubles the request count. On a 250/day budget that halves the
number of fact-checks the product can perform, to buy formatting convenience. So this makes
one grounded call and parses a deliberately small output contract.

**Where the citations come from.** Not the model's prose — from ``grounding_metadata``,
which lists what the search actually retrieved. A URL the model wrote could be invented; a
grounding chunk cannot be. That inverts the usual hallucinated-citation risk for free.

One consequence worth knowing: those chunk URIs are ``vertexaisearch.cloud.google.com``
redirect links rather than publisher URLs. They resolve when clicked, but the trust decision
has to be made on the separate ``domain`` field — see ``app/core/sources.py``.
"""

import asyncio
import logging
import re

from google import genai
from google.genai import types

from app.ai.base import FactCheckProvider, FactCheckUnavailable, ProviderResult, ProviderSource
from app.models.fact_check import FactCheckVerdict

logger = logging.getLogger(__name__)

# The output contract. Small on purpose: every additional required field is another way for
# a parse to fail, and a failed parse costs a request from a daily budget.
_PROMPT = """\
You are fact-checking a single claim made during a live debate. Search for evidence, then \
answer in exactly this format and nothing else:

VERDICT: <one of: true, false, misleading, unverified>
EXPLANATION: <two or three sentences, plain language, no markdown>

Use `misleading` when the claim is technically accurate but omits context that changes its \
meaning. Use `unverified` when your search does not settle it — that is a legitimate answer \
and is much better than guessing. Do not hedge in the verdict line; put every qualification \
in the explanation.

Claim: {claim}"""

_VERDICT_PATTERN = re.compile(r"^\s*VERDICT:\s*([a-z]+)", re.IGNORECASE | re.MULTILINE)
_EXPLANATION_PATTERN = re.compile(
    r"^\s*EXPLANATION:\s*(.+)", re.IGNORECASE | re.MULTILINE | re.DOTALL
)

_VERDICTS: dict[str, FactCheckVerdict] = {v.value: v for v in FactCheckVerdict}


class GeminiFactCheckProvider(FactCheckProvider):
    """Checks a claim with Gemini, grounded in Google Search."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._timeout = timeout_seconds

    async def check(self, claim: str) -> ProviderResult:
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=_PROMPT.format(claim=claim.strip()),
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        # Low temperature: a fact-check should give the same answer twice.
                        temperature=0.0,
                    ),
                ),
                timeout=self._timeout,
            )
        except TimeoutError:
            # Not retried here — the caller owns the budget. See FactCheckProvider.
            logger.warning("Fact-check timed out", extra={"timeout": self._timeout})
            raise FactCheckUnavailable("The fact-check timed out. Try again shortly.") from None
        except Exception as exc:
            # Covers an exhausted daily quota (429) as well as transport failures. Both mean
            # the claim was not checked, which is emphatically not the same as `unverified`.
            logger.warning("Fact-check request failed", exc_info=exc)
            raise FactCheckUnavailable() from exc

        return self._to_result(response)

    def _to_result(self, response: object) -> ProviderResult:
        text = getattr(response, "text", None)
        if not text:
            raise FactCheckUnavailable("The fact-check service returned an empty response.")

        verdict_match = _VERDICT_PATTERN.search(text)
        verdict = _VERDICTS.get(verdict_match.group(1).lower()) if verdict_match else None
        if verdict is None:
            # We cannot read the answer, so we do not have one. Recording `unverified` here
            # would persist a claim that was never actually resolved.
            logger.warning("Unparseable fact-check response", extra={"response": text[:200]})
            raise FactCheckUnavailable("The fact-check service returned an unreadable answer.")

        explanation_match = _EXPLANATION_PATTERN.search(text)
        explanation = (
            explanation_match.group(1).strip()
            if explanation_match
            # The verdict is the load-bearing part; a missing explanation is a cosmetic
            # loss and not worth discarding a request from the daily budget over.
            else "No explanation was provided."
        )

        return ProviderResult(
            verdict=verdict,
            explanation=explanation,
            sources=_extract_sources(response),
        )


def _extract_sources(response: object) -> list[ProviderSource]:
    """Citations from grounding metadata — what search retrieved, not what the model wrote.

    Deliberately tolerant: this walks an SDK response shape that is outside our control, and
    losing the citations is worth far less than losing the verdict. Filtering to trusted
    domains happens in the service layer, in one place, so it can be tested without a model.
    """
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []

    sources: list[ProviderSource] = []
    seen: set[str] = set()
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if web is None:
            continue
        uri = getattr(web, "uri", None)
        if not uri or uri in seen:
            continue
        seen.add(uri)
        sources.append(
            ProviderSource(
                title=getattr(web, "title", None) or getattr(web, "domain", None) or "Source",
                url=uri,
                # The publisher, carried separately because `uri` is a redirect link.
                domain=getattr(web, "domain", None),
            )
        )
    return sources
