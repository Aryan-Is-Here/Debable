"""Application error types and the JSON shape returned for failures.

Every error response has the same body so the frontend can handle them uniformly:

    {"error": {"code": "not_found", "message": "Topic does not exist"}}
"""

from typing import Any


class AppError(Exception):
    """Base class for errors that map to a deliberate HTTP response.

    Raising these (instead of ``HTTPException``) keeps service and repository layers free
    of framework imports; ``app.main`` translates them at the edge.
    """

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            error["details"] = self.details
        return {"error": error}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Resource conflict."


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthenticated"
    message = "Authentication required."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have access to this resource."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "A dependency is unavailable."
