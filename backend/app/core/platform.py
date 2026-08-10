"""Platform-specific runtime adjustments.

psycopg's async driver cannot run on Windows' default ``ProactorEventLoop``; it needs the
selector loop. Linux and macOS are unaffected, and so are Docker containers — this only
matters when a developer runs the API or Alembic directly on Windows.

Call ``configure_event_loop_policy()`` *before* the event loop is created (i.e. before
``asyncio.run`` or ``uvicorn.run``), which is why ``app/__main__.py`` exists rather than
invoking ``uvicorn`` straight from the shell on Windows.
"""

import asyncio
import sys


def configure_event_loop_policy() -> None:
    """Select an event loop policy the database driver can use."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
