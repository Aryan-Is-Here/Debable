"""Async JWKS fetching with a TTL cache.

PyJWT ships ``PyJWKClient``, but it fetches over blocking ``urllib`` — unusable from an
async request handler. This is the same idea built on ``httpx.AsyncClient``.
"""

import asyncio
import logging
import time

import httpx
from jwt import PyJWK, PyJWKSet

logger = logging.getLogger(__name__)


class JWKSError(Exception):
    """Raised when the key set cannot be fetched or the requested key is absent."""


class JWKSCache:
    """Caches a JWKS document and resolves signing keys by ``kid``.

    A cache miss on ``kid`` forces one refetch before failing, so key rotation heals
    without a restart. Refetches are serialised by a lock to avoid a thundering herd.
    """

    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int = 3600,
        timeout_seconds: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._url = url
        self._ttl = ttl_seconds
        self._timeout = timeout_seconds
        # Injected by tests so the suite never makes a real request.
        self._transport = transport
        self._key_set: PyJWKSet | None = None
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def url(self) -> str:
        return self._url

    def _is_stale(self) -> bool:
        return self._key_set is None or (time.monotonic() - self._fetched_at) >= self._ttl

    async def _fetch(self) -> PyJWKSet:
        if not self._url:
            raise JWKSError("No JWKS URL configured; set CLERK_ISSUER or CLERK_JWKS_URL.")
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.get(self._url)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise JWKSError(f"Could not fetch JWKS from {self._url}: {exc}") from exc

        try:
            key_set = PyJWKSet.from_dict(payload)
        except Exception as exc:  # malformed document
            raise JWKSError(f"Malformed JWKS document from {self._url}: {exc}") from exc

        self._key_set = key_set
        self._fetched_at = time.monotonic()
        logger.info("Fetched JWKS", extra={"jwks_url": self._url, "key_count": len(key_set.keys)})
        return key_set

    async def _refresh(self) -> PyJWKSet:
        async with self._lock:
            # Another coroutine may have refreshed while we waited for the lock.
            if not self._is_stale() and self._key_set is not None:
                return self._key_set
            return await self._fetch()

    @staticmethod
    def _find(key_set: PyJWKSet, kid: str) -> PyJWK | None:
        return next((key for key in key_set.keys if key.key_id == kid), None)

    async def get_signing_key(self, kid: str) -> PyJWK:
        """Return the key with this ``kid``, refetching once if it is not cached."""
        key_set = self._key_set
        if self._is_stale() or key_set is None:
            key_set = await self._refresh()

        key = self._find(key_set, kid)
        if key is not None:
            return key

        # Unknown kid on a fresh-enough cache: assume rotation and force one refetch.
        async with self._lock:
            key_set = await self._fetch()
        key = self._find(key_set, kid)
        if key is None:
            raise JWKSError(f"No signing key matching kid={kid!r} in {self._url}")
        return key

    def clear(self) -> None:
        """Drop the cached key set. Used by tests."""
        self._key_set = None
        self._fetched_at = 0.0
