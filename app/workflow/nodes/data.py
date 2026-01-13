"""Data manipulation nodes: GetField, SetField, GetMetadata."""
from typing import Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class GetFieldNode(BaseNode):
    """Reads a field value from the OptionObject into a variable.

    Properties:
        field_number: The field to read (e.g., "123.45")
        output_variable: Variable name to store the value
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the get field operation.

        Reads the field value and stores it in the specified variable.
        """
        import logging
        logger = logging.getLogger(__name__)

        field_number = self.get_property("field_number", "")
        output_var = self.get_property("output_variable", "")

        logger.debug(f"GetFieldNode: field_number='{field_number}', output_var='{output_var}'")
        logger.debug(f"GetFieldNode properties: {self.properties}")

        if field_number and output_var:
            # Resolve field_number in case it's a template
            resolved_field = context.resolve_template(field_number)
            logger.debug(f"GetFieldNode: resolved_field='{resolved_field}'")
            value = context.get_field_value(resolved_field)
            logger.debug(f"GetFieldNode: got value='{value}'")
            context.variables[output_var] = value

        return self.get_output("default")


class SetFieldNode(BaseNode):
    """Writes a value to a field.

    Automatically marks the field as modified and sets RowAction to EDIT.

    Properties:
        field_number: The field to write (e.g., "123.45")
        value: Value or template (e.g., "{{var:name}}")
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the set field operation.

        Resolves templates in the value and writes to the field.
        """
        import logging
        logger = logging.getLogger(__name__)

        field_number = self.get_property("field_number", "")
        value = self.get_property("value", "")

        logger.debug(f"SetFieldNode: field_number='{field_number}', value='{value}'")
        logger.debug(f"SetFieldNode properties: {self.properties}")

        if field_number:
            # Resolve templates
            resolved_field = context.resolve_template(field_number)
            resolved_value = context.resolve_template(value)
            logger.debug(f"SetFieldNode: resolved_field='{resolved_field}', resolved_value='{resolved_value}'")

            # Set the field value
            result = context.set_field_value(resolved_field, resolved_value)
            logger.debug(f"SetFieldNode: set_field_value returned {result}")

        return self.get_output("default")


class GetMetadataNode(BaseNode):
    """Reads OptionObject metadata into a variable.

    Properties:
        property: Which metadata field to read (EntityID, Facility, etc.)
        output_variable: Variable name to store the value
    """

    # Valid metadata properties
    VALID_PROPERTIES = {
        "EntityID",
        "EpisodeNumber",
        "Facility",
        "NamespaceName",
        "OptionId",
        "OptionStaffId",
        "OptionUserId",
        "ParentNamespace",
        "ServerName",
        "SystemCode",
        "SessionToken",
    }

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the get metadata operation.

        Reads the metadata value and stores it in the specified variable.
        """
        prop = self.get_property("property", "")
        output_var = self.get_property("output_variable", "")

        if prop and output_var:
            value = context.get_metadata(prop)
            context.variables[output_var] = value

        return self.get_output("default")


class SetVariableNode(BaseNode):
    """Sets a variable to a static or computed value.

    Properties:
        variable_name: Name of variable to set
        value: Value or template
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the set variable operation."""
        var_name = self.get_property("variable_name", "")
        value = self.get_property("value", "")

        if var_name:
            resolved_value = context.resolve_template(value)
            context.variables[var_name] = resolved_value

        return self.get_output("default")


class MathNode(BaseNode):
    """Perform mathematical operations on values.

    Properties:
        operation: Type of operation (add, subtract, multiply, divide, etc.)
        value_a: First operand (supports templates)
        value_b: Second operand (optional, depends on operation)
        value_c: Third operand (only for clamp: max value)
        output_variable: Variable to store result

    Operations:
        - add: value_a + value_b
        - subtract: value_a - value_b
        - multiply: value_a * value_b
        - divide: value_a / value_b
        - modulo: value_a % value_b
        - min: minimum of value_a and value_b
        - max: maximum of value_a and value_b
        - clamp: clamp value_a between value_b (min) and value_c (max)
        - round: round value_a to nearest integer
        - floor: round value_a down
        - ceil: round value_a up
        - abs: absolute value of value_a
        - parse: extract first number from string value_a
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the math operation."""
        import re
        import math

        operation = self.get_property("operation", "add")
        output_var = self.get_property("output_variable", "")

        if not output_var:
            return self.get_output("default")

        try:
            # Resolve operands
            a_raw = self.get_property("value_a", "")
            b_raw = self.get_property("value_b", "")
            c_raw = self.get_property("value_c", "")

            a_resolved = context.resolve_template(a_raw)
            b_resolved = context.resolve_template(b_raw)
            c_resolved = context.resolve_template(c_raw)

            result = None

            if operation == "add":
                result = self._to_number(a_resolved) + self._to_number(b_resolved)

            elif operation == "subtract":
                result = self._to_number(a_resolved) - self._to_number(b_resolved)

            elif operation == "multiply":
                result = self._to_number(a_resolved) * self._to_number(b_resolved)

            elif operation == "divide":
                b_num = self._to_number(b_resolved)
                if b_num == 0:
                    result = ""  # Avoid division by zero
                else:
                    result = self._to_number(a_resolved) / b_num

            elif operation == "modulo":
                b_num = self._to_number(b_resolved)
                if b_num == 0:
                    result = ""
                else:
                    result = self._to_number(a_resolved) % b_num

            elif operation == "min":
                result = min(self._to_number(a_resolved), self._to_number(b_resolved))

            elif operation == "max":
                result = max(self._to_number(a_resolved), self._to_number(b_resolved))

            elif operation == "clamp":
                value = self._to_number(a_resolved)
                min_val = self._to_number(b_resolved)
                max_val = self._to_number(c_resolved)
                result = max(min_val, min(max_val, value))

            elif operation == "round":
                result = round(self._to_number(a_resolved))

            elif operation == "floor":
                result = math.floor(self._to_number(a_resolved))

            elif operation == "ceil":
                result = math.ceil(self._to_number(a_resolved))

            elif operation == "abs":
                result = abs(self._to_number(a_resolved))

            elif operation == "parse":
                # Extract first number from string
                match = re.search(r'-?\d+\.?\d*', str(a_resolved))
                if match:
                    num_str = match.group()
                    result = float(num_str) if '.' in num_str else int(num_str)
                else:
                    result = 0

            else:
                result = ""

            context.variables[output_var] = result

        except (ValueError, TypeError, ZeroDivisionError):
            # On error, set variable to empty string
            context.variables[output_var] = ""

        return self.get_output("default")

    @staticmethod
    def _to_number(value) -> float:
        """Convert value to number, handling empty strings and None."""
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
