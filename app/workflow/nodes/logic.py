"""Logic and conditional nodes: IfElse, Switch."""
import re
from typing import Any, Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class ConditionalNode(BaseNode):
    """Base class for conditional nodes with true/false outputs.

    Provides common functionality for nodes that evaluate conditions
    and route to either a 'true' or 'false' output port.

    Subclasses should implement:
        evaluate(self, context: ExecutionContext) -> bool
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the conditional evaluation.

        Calls evaluate() to get boolean result, handles exceptions
        by defaulting to False, and returns the appropriate output port.
        """
        try:
            result = self.evaluate(context)
        except Exception:
            result = False

        return self.get_output("true" if result else "false")

    def evaluate(self, context: ExecutionContext) -> bool:
        """Evaluate the condition. Subclasses must override."""
        raise NotImplementedError("Subclasses must implement evaluate()")

    def resolve_value(self, context: ExecutionContext, property_key: str, default: str = "") -> Any:
        """Resolve a property value through template resolution."""
        raw_value = self.get_property(property_key, default)
        return context.resolve_template(raw_value)


class IfElseNode(ConditionalNode):
    """Conditional branching based on a comparison.

    Properties:
        left_value: Value or template for left side
        operator: Comparison operator
        right_value: Value or template for right side (optional for is_empty/is_not_empty)

    Operators:
        ==, !=, >, <, >=, <=, contains, startswith, endswith, matches (regex)
        is_empty, is_not_empty (only uses left_value)

    Output ports:
        true: Taken when condition is true
        false: Taken when condition is false
    """

    @staticmethod
    def _safe_numeric_compare(left: Any, right: Any, compare_func) -> bool:
        """Safely compare two values numerically.

        Falls back to string comparison if numeric conversion fails.
        """
        try:
            left_num = float(left)
            right_num = float(right)
            return compare_func(left_num, right_num)
        except (ValueError, TypeError):
            return compare_func(str(left), str(right))

    @staticmethod
    def _is_empty(value: Any) -> bool:
        """Check if a value is empty, null, or whitespace-only."""
        return value is None or str(value).strip() == ""

    @classmethod
    def get_operator(cls, operator: str):
        """Get the comparison function for an operator."""
        operators = {
            "==": lambda l, r: l == r,
            "!=": lambda l, r: l != r,
            ">": lambda l, r: cls._safe_numeric_compare(l, r, lambda a, b: a > b),
            "<": lambda l, r: cls._safe_numeric_compare(l, r, lambda a, b: a < b),
            ">=": lambda l, r: cls._safe_numeric_compare(l, r, lambda a, b: a >= b),
            "<=": lambda l, r: cls._safe_numeric_compare(l, r, lambda a, b: a <= b),
            "contains": lambda l, r: r in l if l and r else False,
            "startswith": lambda l, r: str(l).startswith(str(r)) if l else False,
            "endswith": lambda l, r: str(l).endswith(str(r)) if l else False,
            "matches": lambda l, r: bool(re.search(r, str(l))) if l and r else False,
            "is_empty": lambda l, r: cls._is_empty(l),
            "is_not_empty": lambda l, r: not cls._is_empty(l),
        }
        return operators.get(operator, lambda l, r: l == r)

    def evaluate(self, context: ExecutionContext) -> bool:
        """Evaluate the comparison condition."""
        left_resolved = self.resolve_value(context, "left_value", "")
        operator = self.get_property("operator", "==")
        right_resolved = self.resolve_value(context, "right_value", "")

        compare_func = self.get_operator(operator)
        return compare_func(left_resolved, right_resolved)


class SwitchNode(BaseNode):
    """Multi-way branching based on value matching.

    Properties:
        value: Value or template to match against cases
        cases: List of {value: string, port: string} mappings
        default_port: Output port if no cases match (default: "default")

    Output ports: Dynamic based on cases configuration + default
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the switch evaluation.

        Returns the port name for the matching case, or default_port if none match.
        """
        default_port = self.get_property("default_port", "default")

        try:
            value = self.get_property("value", "")
            cases = self.get_property("cases", [])

            resolved_value = context.resolve_template(value)

            for case in cases:
                case_value = case.get("value", "")
                case_port = case.get("port", "")
                resolved_case = context.resolve_template(case_value)

                if resolved_value == resolved_case:
                    return self.get_output(case_port)

            return self.get_output(default_port)

        except Exception:
            return self.get_output(default_port)
