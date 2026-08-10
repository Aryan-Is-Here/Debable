"""SQLAlchemy models for the DebateMatch schema (see ``docs/04-database-design.md``).

Importing this package registers every model on ``Base.metadata``, which is what Alembic
autogenerate and the test harness rely on. Import the package, not individual modules.
"""

from app.models.debate_room import DebateRoom
from app.models.fact_check import FactCheck, FactCheckVerdict
from app.models.message import Message
from app.models.rating import Rating
from app.models.topic import Topic, TopicStatus
from app.models.user import User

__all__ = [
    "DebateRoom",
    "FactCheck",
    "FactCheckVerdict",
    "Message",
    "Rating",
    "Topic",
    "TopicStatus",
    "User",
]
