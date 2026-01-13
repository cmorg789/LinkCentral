"""Base node class for workflow nodes."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from app.workflow.context import ExecutionContext


class BaseNode(ABC):
    """Abstract base class for all workflow nodes.

    Each node type must implement the execute method which performs
    the node's operation and returns the next node ID(s) to execute.
    """

    def __init__(self, node_id: str, node_type: str, properties: Dict[str, Any], outputs: Dict[str, str]):
        """Initialize a node.

        Args:
            node_id: Unique identifier for this node instance
            node_type: Type of node (e.g., 'get_field', 'if_else')
            properties: Node-specific configuration
            outputs: Mapping of output port names to target node IDs
        """
        self.node_id = node_id
        self.node_type = node_type
        self.properties = properties
        self.outputs = outputs

    @abstractmethod
    def execute(self, context: ExecutionContext) -> Optional[Union[str, list]]:
        """Execute the node's operation.

        Args:
            context: The execution context containing state

        Returns:
            - None if this is an end node
            - A string node ID for the next node
            - A list of node IDs if multiple branches (only for conditional nodes)
        """
        pass

    def get_output(self, port: str = "default") -> Optional[str]:
        """Get the target node ID for an output port.

        Args:
            port: Name of the output port (default: "default")

        Returns:
            Target node ID or None if port not connected
        """
        return self.outputs.get(port)

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property value with optional default.

        Args:
            key: Property name
            default: Default value if not found

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.node_id})>"
