"""The category allowlist.

Pinned explicitly so that changing it is a deliberate act — the list is mirrored in
``frontend/lib/constants/categories.ts`` and the two must not drift.
"""

from app.core.categories import CATEGORY_MAX_LENGTH, TOPIC_CATEGORIES, is_valid_category


def test_the_allowlist_is_exactly_these_values() -> None:
    assert TOPIC_CATEGORIES == (
        "Technology",
        "Science",
        "Politics",
        "Economics",
        "Society",
        "Ethics",
        "Health",
        "Environment",
        "Education",
        "Culture",
    )


def test_values_are_unique() -> None:
    assert len(set(TOPIC_CATEGORIES)) == len(TOPIC_CATEGORIES)


def test_every_value_fits_the_column() -> None:
    assert max(len(value) for value in TOPIC_CATEGORIES) <= CATEGORY_MAX_LENGTH


def test_validation_is_case_sensitive() -> None:
    assert is_valid_category("Technology")
    assert not is_valid_category("technology")
    assert not is_valid_category("Astrology")
