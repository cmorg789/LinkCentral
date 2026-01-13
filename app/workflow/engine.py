"""Workflow execution engine."""
import json
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.database.models import Workflow
from app.soap.types import OptionObject2015, FormObject, RowObject, FieldObject
from app.workflow.context import ExecutionContext
from app.workflow.nodes import NODE_TYPES, BaseNode


class WorkflowEngine:
    """Executes workflow node pipelines.

    The engine:
    1. Parses workflow definition (nodes + edges)
    2. Creates node instances
    3. Executes nodes in topological order following edges
    4. Builds return OptionObject with only modified fields
    """

    def __init__(self, workflow: Workflow, db: Session):
        """Initialize the engine with a workflow.

        Args:
            workflow: The workflow definition from the database
            db: Database session for potential queries
        """
        self.workflow = workflow
        self.db = db
        self.nodes: Dict[str, BaseNode] = {}
        self.edges: Dict[str, Dict[str, str]] = {}  # node_id -> {port: target_node_id}
        self.context: Optional[ExecutionContext] = None

        self._parse_workflow()

    def _parse_workflow(self) -> None:
        """Parse workflow JSON into node instances and edge mappings."""
        nodes_data = json.loads(self.workflow.nodes) if self.workflow.nodes else []
        edges_data = json.loads(self.workflow.edges) if self.workflow.edges else []

        # Build edge map: source_node_id -> {source_port: target_node_id}
        for edge in edges_data:
            source_id = edge.get("source")
            target_id = edge.get("target")
            source_port = edge.get("sourceHandle", "default")

            if source_id not in self.edges:
                self.edges[source_id] = {}
            self.edges[source_id][source_port] = target_id

        # Create node instances
        for node_data in nodes_data:
            node_id = node_data.get("id")
            node_type = node_data.get("type", "")
            properties = node_data.get("data", {})

            # Get outputs for this node from edges
            outputs = self.edges.get(node_id, {})

            # Get the node class
            node_class = NODE_TYPES.get(node_type)
            if node_class:
                self.nodes[node_id] = node_class(
                    node_id=node_id,
                    node_type=node_type,
                    properties=properties,
                    outputs=outputs,
                )

    def execute(self, option_object: OptionObject2015) -> OptionObject2015:
        """Execute the workflow against an OptionObject.

        Args:
            option_object: The incoming OptionObject2015

        Returns:
            Modified OptionObject2015 with only changed fields
        """
        # Create execution context with db session for nodes that need it
        self.context = ExecutionContext(option_object=option_object, db=self.db)

        # Find start node
        start_node = self._find_start_node()
        if not start_node:
            # No start node - return unmodified
            return self._build_response()

        # Execute nodes
        current_node_id = start_node.node_id
        visited: Set[str] = set()
        max_iterations = 1000  # Prevent infinite loops

        iteration = 0
        while current_node_id and iteration < max_iterations:
            iteration += 1

            # Detect cycles
            if current_node_id in visited:
                # Allow revisiting for loops, but track to prevent infinite
                pass
            visited.add(current_node_id)

            # Get and execute node
            node = self.nodes.get(current_node_id)
            if not node:
                break

            self.context.current_node = current_node_id

            # Execute the node
            next_node_id = node.execute(self.context)

            # Move to next node
            current_node_id = next_node_id

        return self._build_response()

    def _find_start_node(self) -> Optional[BaseNode]:
        """Find the start node in the workflow."""
        for node in self.nodes.values():
            if node.node_type == "start":
                return node
        return None

    def _build_response(self) -> OptionObject2015:
        """Build the response OptionObject with only modified fields.

        Per ScriptLink requirements:
        - Only include FormObjects that have modified RowObjects
        - Only include RowObjects with a RowAction (EDIT)
        - Only include FieldObjects that were modified
        """
        # Note: Spyne ComplexModel objects return False for bool() even when they
        # contain data, so we must use explicit "is not None" checks throughout.

        response = self.context.option_object

        # Set error code and message
        response.ErrorCode = self.context.error_code
        response.ErrorMesg = self.context.error_message

        if not self.context.modified_fields:
            # No modifications - return empty forms
            response.Forms = []
            return response

        # Group modifications by form and row
        modifications: Dict[str, Dict[str, Set[str]]] = {}
        for form_id, row_id, field_number in self.context.modified_fields:
            if form_id not in modifications:
                modifications[form_id] = {}
            if row_id not in modifications[form_id]:
                modifications[form_id][row_id] = set()
            modifications[form_id][row_id].add(field_number)

        # Build response forms
        response_forms = []

        if response.Forms is not None:
            for form in response.Forms:
                if form.FormId not in modifications:
                    continue

                form_mods = modifications[form.FormId]

                # Build modified rows
                response_rows = []

                # Check CurrentRow - use "is not None" because Spyne objects are falsy
                if form.CurrentRow is not None and form.CurrentRow.RowId in form_mods:
                    modified_row = self._build_modified_row(
                        form.CurrentRow,
                        form_mods[form.CurrentRow.RowId]
                    )
                    # Use "is not None" because Spyne ComplexModel objects are falsy
                    if modified_row is not None:
                        response_rows.append(modified_row)

                # Check OtherRows
                if form.OtherRows is not None:
                    for row in form.OtherRows:
                        if row.RowId in form_mods:
                            modified_row = self._build_modified_row(
                                row,
                                form_mods[row.RowId]
                            )
                            # Use "is not None" because Spyne ComplexModel objects are falsy
                            if modified_row is not None:
                                response_rows.append(modified_row)

                if response_rows:
                    # Create response form with only modified rows
                    response_form = FormObject()
                    response_form.FormId = form.FormId
                    response_form.MultipleIteration = form.MultipleIteration

                    # Put first row as CurrentRow, rest as OtherRows
                    response_form.CurrentRow = response_rows[0]
                    response_form.OtherRows = response_rows[1:] if len(response_rows) > 1 else []

                    response_forms.append(response_form)

        response.Forms = response_forms
        return response

    def _build_modified_row(self, original_row: RowObject, modified_field_numbers: Set[str]) -> Optional[RowObject]:
        """Build a row containing only modified fields.

        Args:
            original_row: The original row from the request
            modified_field_numbers: Set of field numbers that were modified

        Returns:
            New RowObject with only modified fields, or None if no fields
        """
        # Note: Spyne ComplexModel objects return False for bool() even when they
        # contain data, so we must use explicit "is None" check.
        if original_row.Fields is None:
            return None

        modified_fields = []
        for field in original_row.Fields:
            if field.FieldNumber in modified_field_numbers:
                modified_fields.append(field)

        if not modified_fields:
            return None

        # Create new row with modified fields
        row = RowObject()
        row.RowId = original_row.RowId
        row.ParentRowId = original_row.ParentRowId
        row.RowAction = "EDIT"  # Mark as edited
        row.Fields = modified_fields

        return row

    def get_context_json(self) -> Optional[str]:
        """Get the execution context as JSON for logging."""
        if self.context:
            return self.context.to_json()
        return None
