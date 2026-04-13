"""ScriptLink script library.

This module provides the API for writing ScriptLink scripts.

Example script:
    from app.scriptlink import OptionObjectWrapper, ValidationError, get_connection

    def run(option_object: OptionObjectWrapper) -> None:
        # Get field values
        name = option_object.fields.get("123.45", "")

        # Set field values (tracked automatically)
        option_object.fields["123.46"] = "Processed"

        # Get metadata
        entity_id = option_object.entity_id
        facility = option_object.facility

        # Query database
        conn = get_connection("AVATAR_DB")
        results = conn.query("SELECT * FROM patients WHERE id = :id", id=entity_id)

        # Set field properties
        option_object.fields["123.47"].required = True
        option_object.fields["123.48"].enabled = False

        # Block form submission with error
        if not name:
            raise ValidationError("Name is required")

        # Debug output (captured by server)
        print(f"Processed patient {entity_id}")
"""
from app.scriptlink.option_object import OptionObjectWrapper, FieldWrapper, FieldAccessor, RowWrapper, from_dict
from app.scriptlink.errors import (
    ScriptLinkError,
    ValidationError,
    AlertError,
    OkCancelError,
    ConfirmError,
    OpenUrlError,
    OpenFormError,
)
from app.scriptlink.sql import SQLHelper
from app.scriptlink.router import ScriptRouter
from app.scriptlink.connections import get_connection
from app.soap.types import ErrorCodes, OptionObject2015

__all__ = [
    # OptionObject wrappers
    "OptionObjectWrapper",
    "FieldWrapper",
    "FieldAccessor",
    "RowWrapper",
    # Types
    "OptionObject2015",
    # Serialization
    "from_dict",
    # Errors
    "ScriptLinkError",
    "ValidationError",
    "AlertError",
    "OkCancelError",
    "ConfirmError",
    "OpenUrlError",
    "OpenFormError",
    # Database
    "get_connection",
    "SQLHelper",
    # Internal
    "ScriptRouter",
    # Constants
    "ErrorCodes",
]
