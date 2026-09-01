"""Application-level exceptions.

All raise a structured ``AppException`` that the FastAPI global handler
renders as JSON ``{"code": ..., "message": ...}`` with the right status code.
"""

from __future__ import annotations


class AppException(Exception):
    """Base class for expected, client-facing application errors."""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class NotFoundError(AppException):
    """A requested resource does not exist."""

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND", 404)


class ConflictError(AppException):
    """The request conflicts with the current state (e.g. duplicate)."""

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message, "CONFLICT", 409)


class ForbiddenError(AppException):
    """The caller is authenticated but not allowed to perform this action."""

    def __init__(self, message: str = "Operation not permitted") -> None:
        super().__init__(message, "FORBIDDEN", 403)


class UnauthorizedError(AppException):
    """The caller is not authenticated or the credentials are invalid."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, "UNAUTHORIZED", 401)


class ValidationError(AppException):
    """The request payload failed a business-rule validation check."""

    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, "VALIDATION_ERROR", 422)
