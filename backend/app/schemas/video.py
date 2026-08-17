"""Video token response models."""

from app.schemas.base import CamelModel


class RoomToken(CamelModel):
    """Everything the browser needs to join the debate's media room.

    Deliberately does not include the API key: the token is already scoped and signed, and
    the client has no use for the credentials that produced it.
    """

    url: str
    """The LiveKit server URL (``wss://…``). Public."""

    token: str
    """Short-lived JWT granting join access to this room as this participant."""

    room_name: str
