"""Flow control nodes: Start, End, and Merge."""
from typing import Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class StartNode(BaseNode):
    """Entry point for every workflow.

    The Start node is automatically created and cannot be deleted.
    It simply passes through to the next connected node.
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the start node.

        Simply returns the next connected node ID.
        """
        return self.get_output("default")


class EndNode(BaseNode):
    """Exit point that finalizes and returns the OptionObject.

    The End node signals completion of the workflow.
    """

    def execute(self, context: ExecutionContext) -> None:
        """Execute the end node.

        Returns None to signal workflow completion.
        """
        return None


class MergeNode(BaseNode):
    """Merge point that converges multiple execution paths.

    The Merge node accepts multiple inputs (in_1, in_2, in_3, in_4) and
    continues execution when ANY input is triggered. This allows branching
    workflows (like If/Else or Switch) to converge back to a single path.

    Since the workflow engine executes a single path at a time (not parallel),
    whichever branch reaches this node first will continue through. The other
    branches are never executed.

    Properties: None
    Input ports: in_1, in_2, in_3, in_4 (multiple inputs)
    Output ports: default
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the merge node.

        Simply passes through to the next connected node. The merging
        behavior is achieved by having multiple input handles that all
        lead to the same execution.
        """
        return self.get_output("default")
