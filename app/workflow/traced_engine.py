"""Workflow engine with execution tracing for simulation."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from app.database.models import Workflow
from app.soap.types import OptionObject2015
from app.workflow.context import ExecutionContext
from app.workflow.engine import WorkflowEngine


@dataclass
class NodeExecutionRecord:
    """Record of a single node's execution state."""

    node_id: str
    node_type: str
    executed: bool = False
    execution_order: Optional[int] = None
    output_port: Optional[str] = None
    input_values: Dict[str, Any] = field(default_factory=dict)
    output_values: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class TracedWorkflowEngine(WorkflowEngine):
    """Extends WorkflowEngine to record execution trace for simulation.

    This engine tracks:
    - Which nodes were executed
    - The order of execution
    - Which output port was taken (for branching nodes)
    - Any errors that occurred
    """

    def __init__(self, workflow: Workflow, db):
        """Initialize the traced engine.

        Args:
            workflow: The workflow definition
            db: Database session
        """
        super().__init__(workflow, db)
        self.execution_records: Dict[str, NodeExecutionRecord] = {}
        self.execution_counter = 0

    def execute(self, option_object: OptionObject2015) -> OptionObject2015:
        """Execute the workflow with tracing enabled.

        Args:
            option_object: The incoming OptionObject2015

        Returns:
            Modified OptionObject2015 with only changed fields
        """
        # Initialize all nodes as not executed
        for node_id, node in self.nodes.items():
            self.execution_records[node_id] = NodeExecutionRecord(
                node_id=node_id,
                node_type=node.node_type,
                executed=False,
            )

        # Create execution context
        self.context = ExecutionContext(option_object=option_object, db=self.db)

        # Find start node
        start_node = self._find_start_node()
        if not start_node:
            return self._build_response()

        # Execute nodes with tracing
        current_node_id = start_node.node_id
        visited: Set[str] = set()
        max_iterations = 1000

        iteration = 0
        while current_node_id and iteration < max_iterations:
            iteration += 1
            visited.add(current_node_id)

            node = self.nodes.get(current_node_id)
            if not node:
                break

            self.context.current_node = current_node_id

            # Capture variables before execution
            vars_before = dict(self.context.variables)

            try:
                next_node_id = node.execute(self.context)
                self._record_node_execution(
                    node_id=current_node_id,
                    next_node_id=next_node_id,
                    vars_before=vars_before,
                    error=None,
                )
            except Exception as e:
                self._record_node_execution(
                    node_id=current_node_id,
                    next_node_id=None,
                    vars_before=vars_before,
                    error=str(e),
                )
                raise

            current_node_id = next_node_id

        return self._build_response()

    def _record_node_execution(
        self,
        node_id: str,
        next_node_id: Optional[str],
        vars_before: Dict[str, Any],
        error: Optional[str],
    ) -> None:
        """Record the execution of a node.

        Args:
            node_id: The executed node's ID
            next_node_id: The next node ID (or None if execution stopped)
            vars_before: Variables dict before this node executed
            error: Error message if execution failed
        """
        self.execution_counter += 1
        record = self.execution_records.get(node_id)

        if record:
            record.executed = True
            record.execution_order = self.execution_counter
            record.error = error

            # Capture any new/changed variables
            vars_after = dict(self.context.variables)
            for key, value in vars_after.items():
                if key not in vars_before or vars_before[key] != value:
                    record.output_values[key] = value

            # Determine which output port was used
            if next_node_id:
                node = self.nodes.get(node_id)
                if node and node.outputs:
                    for port, target in node.outputs.items():
                        if target == next_node_id:
                            record.output_port = port
                            break

    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """Get the execution trace as a list of dictionaries.

        Returns:
            List of node execution records as dicts
        """
        return [
            {
                "node_id": record.node_id,
                "node_type": record.node_type,
                "executed": record.executed,
                "execution_order": record.execution_order,
                "output_port": record.output_port,
                "output_values": record.output_values,
                "error": record.error,
            }
            for record in self.execution_records.values()
        ]

    def get_variables(self) -> Dict[str, Any]:
        """Get the final state of all workflow variables.

        Returns:
            Dictionary of variable names to values
        """
        if self.context:
            return dict(self.context.variables)
        return {}

    def get_modified_fields(self) -> Set[tuple]:
        """Get the set of modified field tuples.

        Returns:
            Set of (form_id, row_id, field_number) tuples
        """
        if self.context:
            return self.context.modified_fields
        return set()
