"""Insert a handful of sample topics into the development database.

    uv run python -m scripts.seed_dev_data          # add sample topics
    uv run python -m scripts.seed_dev_data --clear  # remove them again

Run as a module, not a path: ``python scripts/seed_dev_data.py`` puts ``scripts/`` on the
import path instead of the project root, and ``app`` then fails to import.

Idempotent: topics that already exist are skipped. Development only — it refuses to run
against a production environment.
"""

import asyncio
import sys

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.platform import configure_event_loop_policy
from app.db.session import get_sessionmaker
from app.models import Topic, User

SEED_CLERK_ID = "user_seed_debable"

SAMPLE_TOPICS: list[tuple[str, str, str]] = [
    (
        "Should social media have a minimum age",
        "Some countries are moving to bar under-16s from social platforms entirely. "
        "Is that protection, or is it just paternalism that pushes teenagers somewhere worse?",
        "Society",
    ),
    (
        "Is nuclear power essential to decarbonisation",
        "Renewables are cheaper per megawatt than ever, but they are intermittent. "
        "Does a serious climate plan need new nuclear capacity, or is it a costly distraction?",
        "Environment",
    ),
    (
        "Should AI-generated work be copyrightable",
        "If a model produces an image from a one-line prompt, who owns it — the prompter, "
        "the model's developer, or nobody at all?",
        "Technology",
    ),
    (
        "Are four-day work weeks better for everyone",
        "Trials report happier staff and steady output. Do those results survive contact "
        "with industries that cannot simply compress their hours?",
        "Economics",
    ),
    (
        "Should university tuition be free at the point of use",
        "Free tuition widens access, but somebody pays. Is a general tax the fairest way to "
        "fund a benefit that accrues mostly to graduates?",
        "Education",
    ),
]


async def _seed_user(session) -> User:
    user = await session.scalar(select(User).where(User.clerk_user_id == SEED_CLERK_ID))
    if user is None:
        user = User(
            clerk_user_id=SEED_CLERK_ID,
            username="debable_samples",
            email="samples@debable.local",
            avatar_url=None,
        )
        session.add(user)
        await session.flush()
    return user


async def seed() -> None:
    async with get_sessionmaker()() as session:
        user = await _seed_user(session)
        added = 0
        for title, description, category in SAMPLE_TOPICS:
            exists = await session.scalar(select(Topic).where(Topic.title == title))
            if exists is not None:
                continue
            session.add(
                Topic(
                    title=title,
                    description=description,
                    category=category,
                    creator_id=user.id,
                )
            )
            added += 1
        await session.commit()
        print(f"Seeded {added} topic(s); {len(SAMPLE_TOPICS) - added} already present.")


async def clear() -> None:
    async with get_sessionmaker()() as session:
        user = await session.scalar(select(User).where(User.clerk_user_id == SEED_CLERK_ID))
        if user is None:
            print("Nothing to clear.")
            return
        await session.execute(delete(Topic).where(Topic.creator_id == user.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()
        print("Removed seeded topics and the sample user.")


def main() -> None:
    configure_event_loop_policy()
    if get_settings().is_production:
        raise SystemExit("Refusing to seed a production database.")
    asyncio.run(clear() if "--clear" in sys.argv else seed())


if __name__ == "__main__":
    main()
