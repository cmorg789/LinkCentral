"""Custom exceptions for ScriptLink scripts."""
from app.soap.types import ErrorCodes


class ScriptLinkError(Exception):
    """Base exception for script errors."""

    error_code: float = ErrorCodes.ERROR
    message: str = ""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ValidationError(ScriptLinkError):
    """Raise to block submission with an error message.

    Example:
        if not patient_name:
            raise ValidationError("Patient name is required")
    """

    error_code = ErrorCodes.ERROR


class AlertError(ScriptLinkError):
    """Raise to show an informational popup without blocking.

    Example:
        raise AlertError("Record was updated successfully")
    """

    error_code = ErrorCodes.ALERT


class OkCancelError(ScriptLinkError):
    """Raise to show a message with OK/Cancel buttons.

    Example:
        raise OkCancelError("Do you want to continue?")
    """

    error_code = ErrorCodes.OK_CANCEL


class ConfirmError(ScriptLinkError):
    """Raise to show a Yes/No confirmation dialog.

    Example:
        raise ConfirmError("Are you sure you want to proceed?")
    """

    error_code = ErrorCodes.CONFIRM


class OpenUrlError(ScriptLinkError):
    """Raise to open a URL in the browser.

    Example:
        raise OpenUrlError("https://example.com/patient/123")
    """

    error_code = ErrorCodes.URL


class OpenFormError(ScriptLinkError):
    """Raise to open another form.

    Example:
        raise OpenFormError("FORM_ID")
    """

    error_code = ErrorCodes.OPEN_FORM
