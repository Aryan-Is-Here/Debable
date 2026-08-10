"""Settings parsing."""

from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg,arg-type]


def test_comma_separated_origins_become_a_list() -> None:
    settings = _settings(cors_origins="http://localhost:3000, https://debable.app")

    assert settings.cors_origins == ["http://localhost:3000", "https://debable.app"]


def test_blank_entries_in_a_csv_value_are_dropped() -> None:
    settings = _settings(clerk_authorized_parties="http://localhost:3000,,")

    assert settings.clerk_authorized_parties == ["http://localhost:3000"]


def test_jwks_url_is_derived_from_the_issuer() -> None:
    settings = _settings(clerk_issuer="https://test-app.clerk.accounts.dev/")

    assert (
        settings.resolved_clerk_jwks_url
        == "https://test-app.clerk.accounts.dev/.well-known/jwks.json"
    )


def test_explicit_jwks_url_wins_over_the_issuer() -> None:
    settings = _settings(
        clerk_issuer="https://test-app.clerk.accounts.dev",
        clerk_jwks_url="https://example.com/keys.json",
    )

    assert settings.resolved_clerk_jwks_url == "https://example.com/keys.json"


def test_jwks_url_is_empty_when_clerk_is_unconfigured() -> None:
    assert _settings().resolved_clerk_jwks_url == ""


def test_is_production_tracks_the_env_name() -> None:
    assert _settings(env="production").is_production is True
    assert _settings(env="development").is_production is False
