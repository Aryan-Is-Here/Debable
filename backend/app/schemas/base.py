"""Base model for every API schema.

The frontend's view-models in ``frontend/lib/types.ts`` are camelCase; Python is snake_case.
Rather than hand-writing an alias on every field, all schemas inherit the conversion from
here. FastAPI serialises responses by alias by default, and ``populate_by_name`` means
requests are accepted in either spelling.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
