"""Clerk JWT verification.

Every token here is signed with the locally generated key from ``rsa_key_pair`` and
served through a fake JWKS, so nothing touches Clerk or the network.
"""

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.clerk import ClerkTokenVerifier
from app.auth.dependencies import get_current_claims, get_optional_claims
from app.auth.jwks import JWKSCache, JWKSError
from app.core.config import Settings
from app.core.errors import AuthenticationError
from tests.conftest import TEST_ISSUER, TEST_KID


class FakeJWKS(JWKSCache):
    """JWKS cache serving one in-memory key, counting lookups instead of fetching."""

    def __init__(self, jwk: dict[str, Any]) -> None:
        super().__init__("https://test-app.clerk.accounts.dev/.well-known/jwks.json")
        self._jwk = jwk
        self.lookups = 0

    async def get_signing_key(self, kid: str) -> jwt.PyJWK:
        self.lookups += 1
        if kid != self._jwk["kid"]:
            raise JWKSError(f"No signing key matching kid={kid!r}")
        return jwt.PyJWK.from_dict(self._jwk)


@pytest.fixture
def jwks(rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]) -> FakeJWKS:
    _, jwk = rsa_key_pair
    return FakeJWKS(jwk)


@pytest.fixture
def verifier(settings: Settings, jwks: FakeJWKS) -> ClerkTokenVerifier:
    return ClerkTokenVerifier(settings, jwks=jwks)


def make_token(
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str = TEST_KID,
    **overrides: Any,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "user_2abcDEF",
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 300,
        "azp": "http://localhost:3000",
        "email": "debater@example.com",
        "username": "debater",
        "image_url": "https://img.clerk.com/debater.png",
    }
    claims.update(overrides)
    for key, value in list(claims.items()):
        if value is None:
            del claims[key]
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


class Credentials:
    """Stand-in for ``HTTPAuthorizationCredentials``."""

    def __init__(self, token: str, scheme: str = "Bearer") -> None:
        self.credentials = token
        self.scheme = scheme


async def test_valid_token_is_accepted(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair

    user = await verifier.verify(make_token(private_key))

    assert user.clerk_user_id == "user_2abcDEF"
    assert user.email == "debater@example.com"
    assert user.username == "debater"
    assert user.avatar_url == "https://img.clerk.com/debater.png"


async def test_expired_token_is_rejected(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    past = int(time.time()) - 3600
    token = make_token(private_key, iat=past, exp=past + 60)

    with pytest.raises(AuthenticationError, match="expired"):
        await verifier.verify(token)


async def test_token_from_another_issuer_is_rejected(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    token = make_token(private_key, iss="https://evil.example.com")

    with pytest.raises(AuthenticationError):
        await verifier.verify(token)


async def test_token_signed_by_an_unknown_key_is_rejected(
    verifier: ClerkTokenVerifier,
) -> None:
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(attacker_key, kid="attacker-key")

    with pytest.raises(AuthenticationError):
        await verifier.verify(token)


async def test_token_signed_by_wrong_key_under_a_known_kid_is_rejected(
    verifier: ClerkTokenVerifier,
) -> None:
    # Same kid as the real key, different private key: the signature must not verify.
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(attacker_key)

    with pytest.raises(AuthenticationError):
        await verifier.verify(token)


async def test_token_missing_subject_is_rejected(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    token = make_token(private_key, sub=None)

    with pytest.raises(AuthenticationError):
        await verifier.verify(token)


async def test_token_for_another_origin_is_rejected(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    token = make_token(private_key, azp="https://phishing.example.com")

    with pytest.raises(AuthenticationError, match="another origin"):
        await verifier.verify(token)


async def test_audience_is_checked_when_configured(
    jwks: FakeJWKS, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        env="test",
        clerk_issuer=TEST_ISSUER,
        clerk_audience="debatematch-api",
    )
    verifier = ClerkTokenVerifier(settings, jwks=jwks)

    accepted = await verifier.verify(make_token(private_key, aud="debatematch-api"))
    assert accepted.clerk_user_id == "user_2abcDEF"

    with pytest.raises(AuthenticationError):
        await verifier.verify(make_token(private_key, aud="some-other-api"))


async def test_verification_fails_closed_without_a_configured_issuer(
    jwks: FakeJWKS, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    settings = Settings(_env_file=None, env="test", clerk_issuer="")  # type: ignore[call-arg]
    verifier = ClerkTokenVerifier(settings, jwks=jwks)

    with pytest.raises(AuthenticationError, match="not configured"):
        await verifier.verify(make_token(private_key))


async def test_garbage_token_is_rejected(verifier: ClerkTokenVerifier) -> None:
    with pytest.raises(AuthenticationError, match="Malformed"):
        await verifier.verify("not-a-jwt")


async def test_username_falls_back_to_the_email_local_part(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair

    user = await verifier.verify(make_token(private_key, username=None))

    assert user.username is None
    assert user.fallback_username == "debater"


async def test_username_falls_back_to_the_subject_without_an_email(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair

    user = await verifier.verify(make_token(private_key, username=None, email=None))

    assert user.fallback_username == "user_2abcDEF"


async def test_missing_bearer_header_is_rejected(verifier: ClerkTokenVerifier) -> None:
    with pytest.raises(AuthenticationError, match="Missing bearer token"):
        await get_current_claims(None, verifier)


async def test_non_bearer_scheme_is_rejected(
    verifier: ClerkTokenVerifier, rsa_key_pair: tuple[rsa.RSAPrivateKey, dict[str, Any]]
) -> None:
    private_key, _ = rsa_key_pair
    credentials = Credentials(make_token(private_key), scheme="Basic")

    with pytest.raises(AuthenticationError, match="Bearer"):
        await get_current_claims(credentials, verifier)  # type: ignore[arg-type]


async def test_optional_claims_allow_anonymous_callers(verifier: ClerkTokenVerifier) -> None:
    assert await get_optional_claims(None, verifier) is None
