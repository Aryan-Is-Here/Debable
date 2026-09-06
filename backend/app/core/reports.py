"""The reasons a debate can be reported.

A fixed list rather than free text, for the same reason topic categories are a fixed list:
something you can count is worth more than something you can only read. With no moderation
queue in the MVP nobody reads these individually, so "how many harassment reports" has to be
answerable from the column itself.

Stored as an indexed ``varchar`` validated against this constant, **not** a Postgres enum —
the frontend's radio group has to know the list either way, so an enum would add a migration
to every change without adding protection. Same decision as blueprint conflict #6.

**This list is mirrored in ``frontend/lib/constants/reports.ts``. Change both together.**
"""

from typing import Final

REPORT_CATEGORIES: Final[tuple[str, ...]] = (
    "Harassment",
    "Hate speech",
    "Sexual content",
    "Threats",
    "Spam",
    "Other",
)

# Longest value is "Sexual content" (14); 40 leaves room to add reasons without a migration.
REPORT_CATEGORY_MAX_LENGTH: Final[int] = 40

# Optional context. Bounded because it is a note, not a case file — and because nobody is
# reading it in the MVP, so inviting an essay would be dishonest.
REPORT_DETAIL_MAX_LENGTH: Final[int] = 500


def is_valid_report_category(value: str) -> bool:
    return value in REPORT_CATEGORIES
