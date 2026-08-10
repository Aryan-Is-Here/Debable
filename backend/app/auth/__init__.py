"""Clerk-based authentication.

Clerk owns sign-in entirely (there is no ``POST /auth/login`` — see the locked decision in
``docs/PROJECT-HANDBOOK.md``). The backend only verifies the JWTs the frontend sends.
"""

from app.auth.clerk import ClerkTokenVerifier, ClerkUser, get_token_verifier
from app.auth.dependencies import get_current_claims, get_current_user, get_optional_claims

__all__ = [
    "ClerkTokenVerifier",
    "ClerkUser",
    "get_current_claims",
    "get_current_user",
    "get_optional_claims",
    "get_token_verifier",
]
