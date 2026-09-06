"""Gemini fact-check provider: judges a claim against evidence we retrieved ourselves.

**Why the model does not do its own searching.** It cannot, for free. Verified against the
live API rather than the docs:

* ``gemini-2.5-flash`` — the only model with a free grounding quota on the pricing page —
  returns ``404: no longer available to new users``.
* ``gemini-3.6-flash`` with the ``google_search`` tool returns ``429 RESOURCE_EXHAUSTED`` on
  the *first* call, before any successful generation. That is a zero quota, matching the
  pricing page's "Grounding: Not available" on every 3.x Free Tier row.
* Plain generation on the same models works fine.

Being forced to retrieve separately made the design better in two ways. The allowlist is now
enforced when searching (``app/search/``) instead of filtering citations afterwards, so an
untrusted page is never read. And with no tool in the request, **structured output works** —
Gemini only allows schemas alongside built-in tools from 3.x, and only on paid grounding — so
the verdict is parsed from JSON rather than scraped out of prose.

Citations cannot be invented: the model selects from the numbered sources it was given by
index, and anything outside that range is discarded.
"""

import asyncio
import json
import logging

from google import genai
from google.genai import types

from app.ai.base import FactCheckProvider, FactCheckUnavailable, ProviderResult, ProviderSource
from app.models.fact_check import FactCheckVerdict
from app.search.base import SearchBackend, SearchResult

logger = logging.getLogger(__name__)

# Truncated so one long article cannot crowd the others out of the prompt.
MAX_SOURCE_CHARS = 1500

_SYSTEM = """\
You are fact-checking a single claim made during a live debate. Judge it ONLY against the \
numbered sources provided — you may not rely on anything else you know, because the debaters \
can only check what is cited.

Verdicts:
- true: the sources support the claim.
- false: the sources contradict it.
- misleading: technically accurate but omitting context that changes its meaning.
- unverified: the sources do not settle it. This is a legitimate and useful answer. Prefer it \
over guessing — a confident wrong verdict in a live argument is far worse than an honest \
"cannot tell".

In source_indices, list the numbers of the sources that actually support your verdict. Leave \
it empty if none do. Write the explanation in two or three plain sentences, no markdown."""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [verdict.value for verdict in FactCheckVerdict],
        },
        "explanation": {"type": "string"},
        "source_indices": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["verdict", "explanation", "source_indices"],
}


class GeminiFactCheckProvider(FactCheckProvider):
    """Retrieves evidence, then asks Gemini to judge the claim against it."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        search: SearchBackend,
        timeout_seconds: float,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._search = search
        self._timeout = timeout_seconds

    async def check(self, claim: str) -> ProviderResult:
        cleaned = claim.strip()

        # Raises SearchUnavailable if the search itself failed — which is "never checked",
        # not "checked and unresolved", and so must not reach the model or the database.
        results = await self._search.search(cleaned)

        if not results:
            # An honest verdict: we looked in the trusted sources and found nothing. This is
            # the one place an empty answer is legitimately `unverified` rather than an error.
            return ProviderResult(
                verdict=FactCheckVerdict.UNVERIFIED,
                explanation=(
                    "No trusted source discussing this claim could be found, so it could not "
                    "be confirmed or refuted."
                ),
                sources=[],
            )

        payload = await self._judge(cleaned, results)
        return _to_provider_result(payload, results)

    async def _judge(self, claim: str, results: list[SearchResult]) -> dict:
        prompt = _build_prompt(claim, results)
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM,
                        response_mime_type="application/json",
                        response_schema=_RESPONSE_SCHEMA,
                        # A fact-check should give the same answer to the same evidence twice.
                        temperature=0.0,
                    ),
                ),
                timeout=self._timeout,
            )
        except TimeoutError:
            logger.warning("Fact-check timed out", extra={"timeout": self._timeout})
            raise FactCheckUnavailable("The fact-check timed out. Try again shortly.") from None
        except Exception as exc:  # noqa: BLE001 - quota, transport and API errors alike
            logger.warning("Fact-check request failed", exc_info=exc)
            raise FactCheckUnavailable() from exc

        text = getattr(response, "text", None)
        if not text:
            raise FactCheckUnavailable("The fact-check service returned an empty response.")

        try:
            payload = json.loads(text)
        except ValueError as exc:
            # We cannot read the answer, so we do not have one. Recording `unverified` here
            # would persist a claim that was never actually resolved.
            logger.warning("Unparseable fact-check response", extra={"response": text[:200]})
            raise FactCheckUnavailable(
                "The fact-check service returned an unreadable answer."
            ) from exc

        if not isinstance(payload, dict):
            raise FactCheckUnavailable("The fact-check service returned an unreadable answer.")
        return payload


def _build_prompt(claim: str, results: list[SearchResult]) -> str:
    """Number the sources so the model can cite them by index instead of writing URLs."""
    blocks = [
        f"[{index}] {result.title}\n{result.content[:MAX_SOURCE_CHARS]}"
        for index, result in enumerate(results, start=1)
    ]
    sources = "\n\n".join(blocks)
    return f"Claim: {claim}\n\nSources:\n\n{sources}"


def _to_provider_result(payload: dict, results: list[SearchResult]) -> ProviderResult:
    """Map the model's JSON onto a result, resolving cited indices to real sources."""
    raw_verdict = payload.get("verdict")
    try:
        verdict = FactCheckVerdict(raw_verdict)
    except ValueError:
        logger.warning("Unknown verdict from fact-check", extra={"verdict": raw_verdict})
        raise FactCheckUnavailable(
            "The fact-check service returned an unrecognised verdict."
        ) from None

    explanation = str(payload.get("explanation") or "").strip() or "No explanation was provided."

    # Indices are 1-based in the prompt. Anything out of range is dropped rather than
    # guessed at — this is what makes an invented citation impossible rather than unlikely.
    sources: list[ProviderSource] = []
    seen: set[int] = set()
    for index in payload.get("source_indices") or []:
        if not isinstance(index, int) or index in seen:
            continue
        seen.add(index)
        if 1 <= index <= len(results):
            result = results[index - 1]
            sources.append(ProviderSource(title=result.title, url=result.url))
        else:
            logger.info("Discarding an out-of-range source index", extra={"index": index})

    return ProviderResult(verdict=verdict, explanation=explanation, sources=sources)
