"""Clerk JWT verification.

Verifies signature (RS256 via the issuer's JWKS), expiry, issuer, and — when configured —
audience and authorized party. Returns the claims we care about as a typed object so
callers never poke at raw dictionaries.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from app.auth.jwks import JWKSCache, JWKSError
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError

logger = logging.getLogger(__name__)

_ALGORITHMS = ["RS256"]


@dataclass(frozen=True, slots=True)
class ClerkUser:
    """The subset of a verified Clerk token the application uses."""

    clerk_user_id: str
    email: str | None
    username: str | None
    avatar_url: str | None
    claims: dict[str, Any]

    @property
    def fallback_username(self) -> str:
        """A usable display name even when Clerk sends no username claim.

        Last resort is the Clerk subject itself (already of the form ``user_2abc…``),
        truncated to the 50-character ``users.username`` column.
        """
        if self.username:
            return self.username
        if self.email:
            return self.email.split("@", 1)[0]
        return self.clerk_user_id[:50]


class ClerkTokenVerifier:
    """Verifies Clerk-issued JWTs against the issuer's JWKS."""

    def __init__(self, settings: Settings, jwks: JWKSCache | None = None) -> None:
        self._settings = settings
        self._jwks = jwks or JWKSCache(
            settings.resolved_clerk_jwks_url,
            ttl_seconds=settings.clerk_jwks_cache_seconds,
        )

    async def verify(self, token: str) -> ClerkUser:
        """Verify ``token`` and return its claims, or raise ``AuthenticationError``."""
        if not self._settings.clerk_issuer:
            # Failing closed matters: without an issuer we cannot check who signed this.
            raise AuthenticationError("Authentication is not configured on this server.")

        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Malformed authentication token.") from exc
        if not kid:
            raise AuthenticationError("Authentication token has no key id.")

        try:
            signing_key = await self._jwks.get_signing_key(kid)
        except JWKSError as exc:
            logger.warning("JWKS lookup failed", extra={"kid": kid, "error": str(exc)})
            raise AuthenticationError("Could not verify authentication token.") from exc

        options = {"require": ["exp", "iat", "sub"]}
        audience = self._settings.clerk_audience or None
        try:
            claims = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=_ALGORITHMS,
                issuer=self._settings.clerk_issuer,
                audience=audience,
                options={**options, "verify_aud": audience is not None},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Authentication token has expired.") from exc
        except jwt.PyJWTError as exc:
            logger.info("Token rejected", extra={"error": str(exc)})
            raise AuthenticationError("Invalid authentication token.") from exc

        self._check_authorized_party(claims)
        return self._to_user(claims)

    def _check_authorized_party(self, claims: dict[str, Any]) -> None:
        """Reject tokens minted for an origin we do not serve.

        Clerk puts the requesting origin in ``azp``; checking it blocks a token stolen by
        another site from being replayed against this API.
        """
        allowed = self._settings.clerk_authorized_parties
        if not allowed:
            return
        azp = claims.get("azp")
        if azp is not None and azp not in allowed:
            raise AuthenticationError("Authentication token was issued for another origin.")

    @staticmethod
    def _to_user(claims: dict[str, Any]) -> ClerkUser:
        subject = claims.get("sub")
        if not subject:
            raise AuthenticationError("Authentication token has no subject.")
        return ClerkUser(
            clerk_user_id=subject,
            # Clerk's default session token is lean; these arrive only when the JWT
            # template is customised to include them.
            email=claims.get("email") or claims.get("primary_email_address"),
            username=claims.get("username"),
            avatar_url=claims.get("image_url") or claims.get("picture"),
            claims=claims,
        )


@lru_cache
def get_token_verifier() -> ClerkTokenVerifier:
    """Return the process-wide verifier (its JWKS cache is shared across requests)."""
    return ClerkTokenVerifier(get_settings())
