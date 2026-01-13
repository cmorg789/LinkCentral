"""Execution context for workflow processing."""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from app.soap.types import OptionObject2015, ErrorCodes


@dataclass
class ExecutionContext:
    """Maintains state throughout workflow execution.

    Attributes:
        option_object: The original OptionObject2015 request
        variables: Named variables set during execution
        modified_fields: Set of (form_id, row_id, field_number) tuples that were modified
        error_code: Response error code
        error_message: Response error message
        current_node: Current node ID for debugging
        loop_states: State tracking for active loops
        db: Database session for nodes that need database access
    """

    option_object: OptionObject2015
    variables: Dict[str, Any] = field(default_factory=dict)
    modified_fields: Set[tuple] = field(default_factory=set)
    error_code: float = ErrorCodes.NONE
    error_message: str = ""
    current_node: str = ""
    loop_states: Dict[str, Any] = field(default_factory=dict)
    db: Any = None  # SQLAlchemy Session, typed as Any to avoid circular import

    # Template pattern: @type.key (e.g., @field.123.45, @var.name, @meta.EntityID)
    TEMPLATE_PATTERN = re.compile(r"@(\w+)\.([^\s@]+)")

    def get_field_value(self, field_number: str) -> Optional[str]:
        """Get the value of a field from the OptionObject.

        Args:
            field_number: The field identifier (e.g., "123.45")

        Returns:
            The field value or None if not found
        """
        # Note: Spyne ComplexModel objects return False for bool() even when they
        # contain data, so we must use explicit "is not None" checks throughout.

        if self.option_object.Forms is None:
            return None

        for form in self.option_object.Forms:
            # Check CurrentRow - use "is not None" because Spyne objects are falsy
            if form.CurrentRow is not None and form.CurrentRow.Fields is not None:
                for field_obj in form.CurrentRow.Fields:
                    if field_obj.FieldNumber == field_number:
                        return field_obj.FieldValue

            # Check OtherRows
            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.Fields is not None:
                        for field_obj in row.Fields:
                            if field_obj.FieldNumber == field_number:
                                return field_obj.FieldValue

        return None

    def set_field_value(self, field_number: str, value: str) -> bool:
        """Set the value of a field in the OptionObject.

        Args:
            field_number: The field identifier (e.g., "123.45")
            value: The new value to set

        Returns:
            True if field was found and updated, False otherwise
        """
        # Note: Spyne ComplexModel objects return False for bool() even when they
        # contain data, so we must use explicit "is not None" checks throughout.

        if self.option_object.Forms is None:
            return False

        for form in self.option_object.Forms:
            # Check CurrentRow - use "is not None" because Spyne objects are falsy
            if form.CurrentRow is not None and form.CurrentRow.Fields is not None:
                for field_obj in form.CurrentRow.Fields:
                    if field_obj.FieldNumber == field_number:
                        field_obj.FieldValue = value
                        # Mark as modified
                        self.modified_fields.add((form.FormId, form.CurrentRow.RowId, field_number))
                        return True

            # Check OtherRows
            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.Fields is not None:
                        for field_obj in row.Fields:
                            if field_obj.FieldNumber == field_number:
                                field_obj.FieldValue = value
                                # Mark as modified
                                self.modified_fields.add((form.FormId, row.RowId, field_number))
                                return True

        return False

    def set_field_property(self, field_number: str, prop: str, value: str) -> bool:
        """Set a property (enabled, locked, required) of a field.

        Args:
            field_number: The field identifier
            prop: Property name ('enabled', 'locked', 'required')
            value: '1' or '0'

        Returns:
            True if field was found and updated
        """
        # Note: Spyne ComplexModel objects return False for bool() even when they
        # contain data, so we must use explicit "is not None" checks throughout.

        if self.option_object.Forms is None:
            return False

        prop_map = {
            "enabled": "Enabled",
            "locked": "Lock",  # Note: 'Lock' not 'Locked' per WSDL
            "required": "Required",
        }
        attr_name = prop_map.get(prop.lower())
        if not attr_name:
            return False

        for form in self.option_object.Forms:
            # Check CurrentRow - use "is not None" because Spyne objects are falsy
            if form.CurrentRow is not None and form.CurrentRow.Fields is not None:
                for field_obj in form.CurrentRow.Fields:
                    if field_obj.FieldNumber == field_number:
                        setattr(field_obj, attr_name, value)
                        self.modified_fields.add((form.FormId, form.CurrentRow.RowId, field_number))
                        return True

            # Check OtherRows
            if form.OtherRows is not None:
                for row in form.OtherRows:
                    if row.Fields is not None:
                        for field_obj in row.Fields:
                            if field_obj.FieldNumber == field_number:
                                setattr(field_obj, attr_name, value)
                                self.modified_fields.add((form.FormId, row.RowId, field_number))
                                return True

        return False

    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata from the OptionObject.

        Args:
            key: Metadata field name (EntityID, Facility, OptionUserId, etc.)

        Returns:
            The metadata value or None
        """
        if hasattr(self.option_object, key):
            value = getattr(self.option_object, key)
            return str(value) if value is not None else None
        return None

    def resolve_template(self, value: str) -> str:
        """Resolve template expressions in a string.

        Supported templates:
            @field.123.45 - Value of field 123.45
            @var.name - Value of variable
            @meta.EntityID - OptionObject metadata
            @sql.result_var.0.column - First row, column from SQL result
            @sql.result_var.*.column - All rows, column from SQL result

        Args:
            value: String potentially containing template expressions

        Returns:
            String with templates resolved
        """
        if not value or "@" not in value:
            return value

        def replace_match(match):
            template_type = match.group(1)
            key = match.group(2)

            if template_type == "field":
                result = self.get_field_value(key)
                return result if result is not None else ""

            elif template_type == "var":
                result = self.variables.get(key)
                if result is None:
                    return ""
                return str(result)

            elif template_type == "meta":
                result = self.get_metadata(key)
                return result if result is not None else ""

            elif template_type == "sql":
                # SQL results are stored in variables by the SQL Query node
                # Format: @sql.variable_name.index.column
                # Example: @sql.patients.0.name (first row, name column)
                # Example: @sql.patients.*.id (all rows, id column)
                parts = key.split(".", 2)
                if len(parts) != 3:
                    return ""
                var_name, index_str, column = parts

                sql_result = self.variables.get(var_name)
                if not sql_result or not isinstance(sql_result, list):
                    return ""

                if index_str == "*":
                    # Return all values as comma-separated
                    return ",".join(str(row.get(column, "")) for row in sql_result)
                else:
                    try:
                        index = int(index_str)
                        if 0 <= index < len(sql_result):
                            return str(sql_result[index].get(column, ""))
                    except (ValueError, IndexError):
                        pass
                    return ""

            return match.group(0)  # Return original if unknown

        return self.TEMPLATE_PATTERN.sub(replace_match, value)

    def to_json(self) -> str:
        """Serialize context to JSON for logging."""
        return json.dumps({
            "variables": {k: str(v) for k, v in self.variables.items()},
            "modified_fields": [list(f) for f in self.modified_fields],
            "error_code": self.error_code,
            "error_message": self.error_message,
            "current_node": self.current_node,
        })
