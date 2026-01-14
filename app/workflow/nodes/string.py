"""String manipulation nodes: StringNode."""
from typing import Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class StringNode(BaseNode):
    """Perform string operations on values.

    Properties:
        operation: Type of operation (concat, uppercase, lowercase, trim, length, replace)
        value_a: First string (required, supports templates)
        value_b: Second string (for concat, replace - the search string)
        value_c: Third string (for replace - the replacement string)
        output_variable: Variable to store result

    Operations:
        - concat: Concatenate value_a and value_b
        - uppercase: Convert value_a to uppercase
        - lowercase: Convert value_a to lowercase
        - trim: Remove leading/trailing whitespace from value_a
        - length: Get the length of value_a
        - replace: Replace value_b with value_c in value_a
        - to_string: Cast value_a to string
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the string operation."""
        operation = self.get_property("operation", "concat")
        output_var = self.get_property("output_variable", "")

        if not output_var:
            return self.get_output("default")

        try:
            # Resolve operands
            a_raw = self.get_property("value_a", "")
            b_raw = self.get_property("value_b", "")
            c_raw = self.get_property("value_c", "")

            a_resolved = str(context.resolve_template(a_raw)) if a_raw else ""
            b_resolved = str(context.resolve_template(b_raw)) if b_raw else ""
            c_resolved = str(context.resolve_template(c_raw)) if c_raw else ""

            result = None

            if operation == "concat":
                result = a_resolved + b_resolved

            elif operation == "uppercase":
                result = a_resolved.upper()

            elif operation == "lowercase":
                result = a_resolved.lower()

            elif operation == "trim":
                result = a_resolved.strip()

            elif operation == "length":
                result = len(a_resolved)

            elif operation == "replace":
                # Replace all occurrences of b_resolved with c_resolved in a_resolved
                if b_resolved:
                    result = a_resolved.replace(b_resolved, c_resolved)
                else:
                    result = a_resolved

            elif operation == "to_string":
                # Cast to string - handles any type including numbers, booleans, None
                # resolve_template converts to string, so we need to handle numeric strings
                raw_value = context.resolve_template(a_raw)
                if raw_value is None or raw_value == "":
                    result = ""
                elif isinstance(raw_value, float):
                    # Direct float value
                    if raw_value.is_integer():
                        result = str(int(raw_value))
                    else:
                        result = str(raw_value)
                elif isinstance(raw_value, str):
                    # Check if it's a numeric string like "5.0"
                    try:
                        num = float(raw_value)
                        if num.is_integer():
                            result = str(int(num))
                        else:
                            result = raw_value
                    except ValueError:
                        # Not a number, just return as-is
                        result = raw_value
                else:
                    result = str(raw_value)

            else:
                result = ""

            context.variables[output_var] = result

        except (ValueError, TypeError, AttributeError):
            # On error, set variable to empty string
            context.variables[output_var] = ""

        return self.get_output("default")
