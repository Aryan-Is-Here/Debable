"""Response models shared across resources."""

from typing import Generic, TypeVar

from pydantic import Field

from app.schemas.base import CamelModel

T = TypeVar("T")


class Page(CamelModel, Generic[T]):
    """A slice of a larger collection.

    Offset/limit rather than cursors: topic lists are small, sorted by recency rather than
    strictly by an opaque key, and the UI wants a total so it can say "N of M".
    """

    items: list[T]
    total: int = Field(description="Total matching rows, ignoring limit and offset.")
    limit: int
    offset: int
