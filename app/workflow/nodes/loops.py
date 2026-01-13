"""Loop nodes for iteration control."""
from typing import Any, Dict, List, Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class LoopCountNode(BaseNode):
    """Loops a specified number of times.

    Properties:
        count: Number of iterations (int or template)
        index_variable: Variable name for current index (0-based)

    Output ports:
        each: Executed for each iteration
        done: Executed after all iterations complete

    Input ports:
        default: Entry point (first entry)
        loop_in: Return point from loop body

    The loop body should connect back to this node's loop_in port.
    When execution returns via loop_in, the loop advances to the next iteration.
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the loop iteration logic."""
        count_value = self.get_property("count", 0)
        index_variable = self.get_property("index_variable", "loop_index")

        # Resolve count if it's a template
        if isinstance(count_value, str):
            resolved = context.resolve_template(count_value)
            try:
                count = int(resolved)
            except (ValueError, TypeError):
                count = 0
        else:
            count = int(count_value)

        # Get or initialize loop state
        if not hasattr(context, 'loop_states'):
            context.loop_states = {}

        loop_state = context.loop_states.get(self.node_id)

        if loop_state is None:
            # First entry - initialize loop
            if count <= 0:
                # No iterations needed
                return self.get_output("done")

            context.loop_states[self.node_id] = {
                "current_index": 0,
                "max_count": count,
            }
            context.variables[index_variable] = 0
            return self.get_output("each")

        else:
            # Re-entry from loop body - advance to next iteration
            current_index = loop_state["current_index"] + 1
            max_count = loop_state["max_count"]

            if current_index >= max_count:
                # Loop complete - clean up and exit
                del context.loop_states[self.node_id]
                return self.get_output("done")

            # Continue loop
            loop_state["current_index"] = current_index
            context.variables[index_variable] = current_index
            return self.get_output("each")


class LoopRowsNode(BaseNode):
    """Iterates over all rows in a multiple-iteration form.

    Properties:
        form_id: The form ID to iterate over
        row_variable: Variable name for current row data (dict of field_number -> value)
        index_variable: Variable name for current index (0-based)

    Output ports:
        each: Executed for each row
        done: Executed after all rows complete

    Input ports:
        default: Entry point (first entry)
        loop_in: Return point from loop body

    The loop body should connect back to this node's loop_in port.
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the row iteration logic."""
        form_id = self.get_property("form_id", "")
        row_variable = self.get_property("row_variable", "current_row")
        index_variable = self.get_property("index_variable", "row_index")

        # Resolve form_id if it's a template
        resolved_form_id = context.resolve_template(form_id)

        # Get or initialize loop state
        if not hasattr(context, 'loop_states'):
            context.loop_states = {}

        loop_state = context.loop_states.get(self.node_id)

        if loop_state is None:
            # First entry - collect all rows from the form
            rows = self._collect_rows(context, resolved_form_id)

            if not rows:
                # No rows to iterate
                return self.get_output("done")

            context.loop_states[self.node_id] = {
                "current_index": 0,
                "rows": rows,
            }

            # Set variables for first row
            context.variables[index_variable] = 0
            context.variables[row_variable] = rows[0]
            return self.get_output("each")

        else:
            # Re-entry from loop body - advance to next row
            current_index = loop_state["current_index"] + 1
            rows = loop_state["rows"]

            if current_index >= len(rows):
                # Loop complete - clean up and exit
                del context.loop_states[self.node_id]
                return self.get_output("done")

            # Continue loop
            loop_state["current_index"] = current_index
            context.variables[index_variable] = current_index
            context.variables[row_variable] = rows[current_index]
            return self.get_output("each")

    def _collect_rows(self, context: ExecutionContext, form_id: str) -> List[Dict[str, Any]]:
        """Collect all rows from a form as list of field dicts.

        Args:
            context: Execution context with OptionObject
            form_id: Form ID to collect rows from

        Returns:
            List of dicts, each mapping field_number -> field_value
        """
        rows = []

        if not context.option_object.Forms:
            return rows

        for form in context.option_object.Forms:
            if form.FormId != form_id:
                continue

            # Collect CurrentRow
            if form.CurrentRow and form.CurrentRow.Fields:
                row_data = {
                    "_row_id": form.CurrentRow.RowId,
                    "_parent_row_id": form.CurrentRow.ParentRowId,
                }
                for field in form.CurrentRow.Fields:
                    row_data[field.FieldNumber] = field.FieldValue
                rows.append(row_data)

            # Collect OtherRows
            if form.OtherRows:
                for row in form.OtherRows:
                    if row.Fields:
                        row_data = {
                            "_row_id": row.RowId,
                            "_parent_row_id": row.ParentRowId,
                        }
                        for field in row.Fields:
                            row_data[field.FieldNumber] = field.FieldValue
                        rows.append(row_data)

            break  # Found the form, no need to continue

        return rows
