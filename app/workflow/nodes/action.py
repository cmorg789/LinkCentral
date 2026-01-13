"""Action nodes: SetError, SetFieldProperty."""
from typing import Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext
from app.soap.types import ErrorCodes


class SetErrorNode(BaseNode):
    """Sets the response error code and message.

    Properties:
        error_code: Error code (0-6)
        message: Message text or template

    Error Codes:
        0 = None (success)
        1 = Error (blocks form submission)
        2 = OkCancel
        3 = Alert (informational)
        4 = Confirm
        5 = URL
        6 = OpenForm
    """

    ERROR_CODE_MAP = {
        "0": ErrorCodes.NONE,
        "1": ErrorCodes.ERROR,
        "2": ErrorCodes.OK_CANCEL,
        "3": ErrorCodes.ALERT,
        "4": ErrorCodes.CONFIRM,
        "5": ErrorCodes.URL,
        "6": ErrorCodes.OPEN_FORM,
        # Also accept string names
        "none": ErrorCodes.NONE,
        "error": ErrorCodes.ERROR,
        "okcancel": ErrorCodes.OK_CANCEL,
        "alert": ErrorCodes.ALERT,
        "confirm": ErrorCodes.CONFIRM,
        "url": ErrorCodes.URL,
        "openform": ErrorCodes.OPEN_FORM,
    }

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the set error operation.

        Sets error code and message on the context.
        """
        error_code = self.get_property("error_code", "0")
        message = self.get_property("message", "")

        # Resolve error code
        code_value = self.ERROR_CODE_MAP.get(str(error_code).lower(), ErrorCodes.NONE)
        context.error_code = code_value

        # Resolve message template
        context.error_message = context.resolve_template(message)

        return self.get_output("default")


class SetFieldPropertyNode(BaseNode):
    """Modifies field properties (enabled, locked, required).

    Properties:
        field_number: The field to modify
        property: Property name ('enabled', 'locked', 'required')
        value: 'true' or 'false' (or '1'/'0')
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the set field property operation."""
        field_number = self.get_property("field_number", "")
        prop = self.get_property("property", "")
        value = self.get_property("value", "")

        if field_number and prop:
            # Resolve field number template
            resolved_field = context.resolve_template(field_number)

            # Convert value to '1' or '0'
            if value.lower() in ("true", "1", "yes"):
                prop_value = "1"
            else:
                prop_value = "0"

            context.set_field_property(resolved_field, prop, prop_value)

        return self.get_output("default")
