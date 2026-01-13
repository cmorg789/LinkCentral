"""Workflow node implementations."""
from .base import BaseNode
from .flow import StartNode, EndNode, MergeNode
from .data import GetFieldNode, SetFieldNode, GetMetadataNode, SetVariableNode, MathNode
from .string import StringNode
from .logic import ConditionalNode, IfElseNode, SwitchNode
from .action import SetErrorNode, SetFieldPropertyNode
from .sql import SQLQueryNode
from .http import HTTPRequestNode
from .script import PythonScriptNode
from .loops import LoopCountNode, LoopRowsNode

NODE_TYPES = {
    # Flow nodes
    "start": StartNode,
    "end": EndNode,
    "merge": MergeNode,
    # Data nodes
    "get_field": GetFieldNode,
    "set_field": SetFieldNode,
    "get_metadata": GetMetadataNode,
    "set_variable": SetVariableNode,
    "math": MathNode,
    "string": StringNode,
    "sql_query": SQLQueryNode,
    # Logic nodes
    "if_else": IfElseNode,
    "switch": SwitchNode,
    # Action nodes
    "set_error": SetErrorNode,
    "set_field_property": SetFieldPropertyNode,
    # HTTP node
    "http_request": HTTPRequestNode,
    # Script node
    "python_script": PythonScriptNode,
    # Loop nodes
    "loop_count": LoopCountNode,
    "loop_rows": LoopRowsNode,
}

__all__ = [
    "BaseNode",
    # Flow
    "StartNode",
    "EndNode",
    "MergeNode",
    # Data
    "GetFieldNode",
    "SetFieldNode",
    "GetMetadataNode",
    "SetVariableNode",
    "MathNode",
    "StringNode",
    "SQLQueryNode",
    # Logic
    "ConditionalNode",
    "IfElseNode",
    "SwitchNode",
    # Action
    "SetErrorNode",
    "SetFieldPropertyNode",
    # HTTP
    "HTTPRequestNode",
    # Script
    "PythonScriptNode",
    # Loops
    "LoopCountNode",
    "LoopRowsNode",
    # Registry
    "NODE_TYPES",
]
