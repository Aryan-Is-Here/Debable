"""JWKS caching, key rotation and failure handling."""

from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.jwks import JWKSCache, JWKSError

JWKS_URL = "https://test-app.clerk.accounts.dev/.well-known/jwks.json"


class RecordingTransport(httpx.AsyncBaseTransport):
    """Serves a scripted sequence of JWKS documents and counts requests."""

    def __init__(self, *responses: httpx.Response) -> None:
        self._responses = list(responses)
        self.request_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        # The last scripted response repeats once the script runs out.
        index = min(self.request_count - 1, len(self._responses) - 1)
        return self._responses[index]


def jwk_document(*jwks: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"keys": list(jwks)})


async def test_key_set_is_fetched_once_and_reused(rsa_key_pair) -> None:
    _, jwk = rsa_key_pair
    transport = RecordingTransport(jwk_document(jwk))
    cache = JWKSCache(JWKS_URL, transport=transport)

    first = await cache.get_signing_key(jwk["kid"])
    second = await cache.get_signing_key(jwk["kid"])

    assert first.key_id == second.key_id
    assert transport.request_count == 1


async def test_expired_cache_is_refetched(rsa_key_pair) -> None:
    _, jwk = rsa_key_pair
    transport = RecordingTransport(jwk_document(jwk))
    cache = JWKSCache(JWKS_URL, ttl_seconds=0, transport=transport)

    await cache.get_signing_key(jwk["kid"])
    await cache.get_signing_key(jwk["kid"])

    assert transport.request_count == 2


async def test_unknown_kid_triggers_one_refetch_then_succeeds(rsa_key_pair) -> None:
    """A rotated key must heal without restarting the process."""
    _, old_jwk = rsa_key_pair
    rotated_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    import jwt as pyjwt

    new_jwk: dict[str, Any] = pyjwt.algorithms.RSAAlgorithm.to_jwk(  # type: ignore[assignment]
        rotated_key.public_key(), as_dict=True
    )
    new_jwk.update({"kid": "rotated-key", "alg": "RS256", "use": "sig"})

    transport = RecordingTransport(jwk_document(old_jwk), jwk_document(old_jwk, new_jwk))
    cache = JWKSCache(JWKS_URL, transport=transport)

    await cache.get_signing_key(old_jwk["kid"])
    resolved = await cache.get_signing_key("rotated-key")

    assert resolved.key_id == "rotated-key"
    assert transport.request_count == 2


async def test_kid_absent_after_refetch_raises(rsa_key_pair) -> None:
    _, jwk = rsa_key_pair
    transport = RecordingTransport(jwk_document(jwk))
    cache = JWKSCache(JWKS_URL, transport=transport)

    with pytest.raises(JWKSError, match="No signing key"):
        await cache.get_signing_key("never-existed")


async def test_http_failure_raises_jwks_error(rsa_key_pair) -> None:
    transport = RecordingTransport(httpx.Response(500, text="boom"))
    cache = JWKSCache(JWKS_URL, transport=transport)

    with pytest.raises(JWKSError, match="Could not fetch JWKS"):
        await cache.get_signing_key("any")


async def test_missing_url_raises_jwks_error() -> None:
    cache = JWKSCache("")

    with pytest.raises(JWKSError, match="No JWKS URL configured"):
        await cache.get_signing_key("any")
