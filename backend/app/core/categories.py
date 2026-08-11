"""The allowed topic categories.

Category is a browse filter, not a domain concept — nothing in the application branches on
its value. So it lives as a plain indexed ``varchar`` validated against this list rather
than as a Postgres enum: the frontend's ``<Select>`` has to know the list either way, so an
enum would add a migration to every change without adding protection. See blueprint
conflict #6 in ``docs/PROJECT-HANDBOOK.md``.

**This list is mirrored in ``frontend/lib/constants/categories.ts``. Change both together.**
"""

from typing import Final

TOPIC_CATEGORIES: Final[tuple[str, ...]] = (
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

# Longest value is "Environment" (11); 40 leaves room to add categories without a migration.
CATEGORY_MAX_LENGTH: Final[int] = 40


def is_valid_category(value: str) -> bool:
    return value in TOPIC_CATEGORIES
