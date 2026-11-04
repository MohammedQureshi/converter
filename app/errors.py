"""Error model. Every failure leaves the service as JSON: {error, message, requestId}."""

from __future__ import annotations


class ApiError(Exception):
    """An error with an HTTP status and a stable machine-readable code."""

    status = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status

    def __reduce__(self):
        # Keeps errors picklable, since they cross the engine-process boundary.
        return (_rebuild, (type(self), self.message, self.code, self.status))


def _rebuild(cls, message, code, status):
    return cls(message, code=code, status=status)


class BadRequest(ApiError):
    status = 400
    code = "BAD_REQUEST"


class Unauthorized(ApiError):
    status = 401
    code = "UNAUTHORIZED"


class NotFound(ApiError):
    status = 404
    code = "NOT_FOUND"


class MethodNotAllowed(ApiError):
    status = 405
    code = "METHOD_NOT_ALLOWED"


class FileTooLarge(ApiError):
    status = 413
    code = "FILE_TOO_LARGE"


class UnsupportedFormat(ApiError):
    status = 415
    code = "UNSUPPORTED_FORMAT"


class EncryptedFile(ApiError):
    status = 422
    code = "ENCRYPTED_FILE"


class CorruptFile(ApiError):
    status = 422
    code = "CORRUPT_FILE"


class TooManyPages(ApiError):
    status = 422
    code = "TOO_MANY_PAGES"


class PdfaValidationFailed(ApiError):
    status = 422
    code = "PDFA_VALIDATION_FAILED"


class ConversionFailed(ApiError):
    """An engine failed on input that was not identifiably bad."""

    status = 500
    code = "CONVERSION_FAILED"


class ConversionTimeout(ApiError):
    status = 504
    code = "CONVERSION_TIMEOUT"
