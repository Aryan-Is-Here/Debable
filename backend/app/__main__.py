"""Development entrypoint: ``uv run python -m app``.

Sets the event loop policy before uvicorn creates the loop (see ``core.platform``), then
starts the server. In Docker the image runs ``uvicorn`` directly — Linux needs no shim.
"""

import uvicorn

from app.core.config import get_settings
from app.core.platform import configure_event_loop_policy


def main() -> None:
    configure_event_loop_policy()
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=not settings.is_production,
        log_config=None,  # logging is configured by app.core.logging
    )


if __name__ == "__main__":
    main()
