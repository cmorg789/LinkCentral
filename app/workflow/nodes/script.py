"""Python Script node for custom code execution."""
import signal
import threading
from typing import Any, Optional

from app.workflow.nodes.base import BaseNode
from app.workflow.context import ExecutionContext


class ScriptTimeoutError(Exception):
    """Raised when script execution exceeds timeout."""
    pass


class PythonScriptNode(BaseNode):
    """Executes custom Python code.

    Properties:
        code: Python code to execute
        input_variables: List of variable names to make available to script
        output_variable: Variable name to store result
        timeout: Execution timeout in seconds (default 5)

    The script has access to:
        - `inputs`: dict containing values of specified input variables
        - `result`: must be set by the script to provide output

    Example script:
        # inputs contains {"patient_name": "John", "age": 30}
        if inputs.get("age", 0) >= 18:
            result = "adult"
        else:
            result = "minor"

    NOTE: No sandboxing is applied. Use with caution.
    """

    def execute(self, context: ExecutionContext) -> Optional[str]:
        """Execute the Python script and store result."""
        code = self.get_property("code", "")
        input_variables = self.get_property("input_variables", [])
        output_variable = self.get_property("output_variable", "script_result")
        timeout = self.get_property("timeout", 5)

        if not code:
            return self.get_output("default")

        # Build inputs dict from specified variables
        inputs = {}
        for var_name in input_variables:
            if var_name in context.variables:
                inputs[var_name] = context.variables[var_name]

        # Create execution namespace
        namespace = {
            "inputs": inputs,
            "result": None,
        }

        # Execute with timeout
        error = None
        result_holder = {"value": None, "error": None}

        def run_script():
            try:
                exec(code, namespace)
                result_holder["value"] = namespace.get("result")
            except Exception as e:
                result_holder["error"] = str(e)

        thread = threading.Thread(target=run_script)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Script timed out - we can't forcefully kill the thread,
            # but we can record the timeout and continue
            context.variables[output_variable] = None
            context.variables[f"{output_variable}_error"] = f"Script execution timed out after {timeout} seconds"
        elif result_holder["error"]:
            context.variables[output_variable] = None
            context.variables[f"{output_variable}_error"] = result_holder["error"]
        else:
            context.variables[output_variable] = result_holder["value"]

        return self.get_output("default")
