"""Test runner for ScriptLink scripts.

Runs scripts locally using captured OptionObject JSON fixtures.

Usage:
    python -m app.scriptlink test PARAM fixture.json [--verbose]
"""
import io
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.scriptlink.option_object import OptionObjectWrapper, from_dict
from app.scriptlink.router import ScriptRouter
from app.scriptlink.errors import ScriptLinkError
from app.soap.types import OptionObject2015, ErrorCodes

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class TestResult:
    """Result of running a script test."""
    success: bool
    response: Optional[OptionObject2015] = None
    diff: Optional[Dict[str, Dict[str, Any]]] = None
    stdout: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: int = 0


def load_fixture(path: Path) -> OptionObject2015:
    """Load and deserialize JSON fixture file.

    Args:
        path: Path to JSON fixture file

    Returns:
        Deserialized OptionObject2015

    Raises:
        FileNotFoundError: If fixture file doesn't exist
        json.JSONDecodeError: If fixture isn't valid JSON
    """
    with open(path) as f:
        data = json.load(f)
    return from_dict(data)


def run_script_test(parameter: str, option_object: OptionObject2015) -> TestResult:
    """Execute a script with the given OptionObject.

    Matches the execution behavior of the SOAP service, including
    stdout capture and error handling.

    Args:
        parameter: Script parameter name (filename without .py)
        option_object: Deserialized OptionObject2015 fixture

    Returns:
        TestResult with response, diff, stdout, and any errors
    """
    start_time = time.time()

    # Get script handler
    router = ScriptRouter(SCRIPTS_DIR, DATA_DIR)
    handler = router.get_handler(parameter)

    if handler is None:
        return TestResult(
            success=False,
            error=f"Script not found: scripts/{parameter}.py",
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    # Create wrapper
    wrapper = OptionObjectWrapper(option_object)

    # Capture stdout
    captured = io.StringIO()
    old_stdout = sys.stdout

    try:
        sys.stdout = captured
        result = handler(wrapper)

        # Build response from wrapper if None returned
        if result is None:
            result = wrapper.build_response()

        execution_time_ms = int((time.time() - start_time) * 1000)

        return TestResult(
            success=True,
            response=result,
            diff=wrapper.get_diff(),
            stdout=captured.getvalue(),
            error=result.ErrorMesg if result.ErrorCode != ErrorCodes.NONE else None,
            error_type=_error_code_name(result.ErrorCode) if result.ErrorCode != ErrorCodes.NONE else None,
            execution_time_ms=execution_time_ms
        )

    except ScriptLinkError as e:
        # Handle ValidationError, AlertError, etc.
        result = wrapper.build_response()
        result.ErrorCode = e.error_code
        result.ErrorMesg = str(e)

        return TestResult(
            success=True,
            response=result,
            diff=wrapper.get_diff(),
            stdout=captured.getvalue(),
            error=str(e),
            error_type=type(e).__name__,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        # Unexpected error
        import traceback
        return TestResult(
            success=False,
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            error_type=type(e).__name__,
            stdout=captured.getvalue(),
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    finally:
        sys.stdout = old_stdout


def _error_code_name(code: float) -> str:
    """Get human-readable name for error code."""
    names = {
        ErrorCodes.NONE: "NONE",
        ErrorCodes.ERROR: "ERROR",
        ErrorCodes.OK_CANCEL: "OK_CANCEL",
        ErrorCodes.ALERT: "ALERT",
        ErrorCodes.CONFIRM: "CONFIRM",
        ErrorCodes.URL: "URL",
        ErrorCodes.OPEN_FORM: "OPEN_FORM",
    }
    return names.get(code, f"UNKNOWN({code})")


def format_output(result: TestResult, verbose: bool = False) -> str:
    """Format test results for console display.

    Args:
        result: TestResult from run_script_test
        verbose: If True, include stdout output

    Returns:
        Formatted string for printing
    """
    lines = []

    # Header
    if result.success:
        lines.append(f"Script executed successfully in {result.execution_time_ms}ms")
    else:
        lines.append(f"Script failed in {result.execution_time_ms}ms")

    lines.append("")

    # Error info
    if result.error:
        error_label = result.error_type or "Error"
        lines.append(f"{error_label}: {result.error.split(chr(10))[0]}")
        lines.append("")

    # Response info
    if result.response:
        code_name = _error_code_name(result.response.ErrorCode)
        lines.append("Response:")
        lines.append(f"  ErrorCode: {int(result.response.ErrorCode)} ({code_name})")
        if result.response.ErrorMesg:
            lines.append(f"  ErrorMesg: {result.response.ErrorMesg}")
        lines.append("")

    # Diff
    if result.diff:
        # Field changes (skip row operation keys)
        field_changes = {
            k: v for k, v in result.diff.items()
            if k not in ("added_rows", "deleted_rows")
        }
        if field_changes:
            lines.append(f"Changes ({len(field_changes)} field{'s' if len(field_changes) != 1 else ''}):")
            for field_num, changes in field_changes.items():
                lines.append(f"  {field_num}:")
                for prop, vals in changes.items():
                    old = vals.get("old", "")
                    new = vals.get("new", "")
                    lines.append(f"    {prop}: {repr(old)} -> {repr(new)}")
            lines.append("")

        # Added rows
        added_rows = result.diff.get("added_rows", [])
        if added_rows:
            lines.append(f"Added rows ({len(added_rows)}):")
            for row_info in added_rows:
                lines.append(f"  Form {row_info['form_id']}, RowId {row_info['row_id']}:")
                for field_num, value in row_info.get("values", {}).items():
                    lines.append(f"    {field_num}: {repr(value)}")
            lines.append("")

        # Deleted rows
        deleted_rows = result.diff.get("deleted_rows", [])
        if deleted_rows:
            lines.append(f"Deleted rows ({len(deleted_rows)}):")
            for row_info in deleted_rows:
                lines.append(f"  Form {row_info['form_id']}, RowId {row_info['row_id']}")
            lines.append("")

        if not field_changes and not added_rows and not deleted_rows:
            lines.append("No field changes.")
            lines.append("")
    elif result.success:
        lines.append("No field changes.")
        lines.append("")

    # Stdout (verbose only)
    if verbose and result.stdout:
        lines.append("Script Output:")
        for line in result.stdout.rstrip().split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    return "\n".join(lines)


def main(args):
    """Run a script test from parsed CLI arguments.

    Args:
        args: Namespace with parameter, fixture, and verbose attributes.
    """
    # Load fixture
    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = PROJECT_ROOT / fixture_path

    if not fixture_path.exists():
        print(f"Error: Fixture file not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    try:
        option_object = load_fixture(fixture_path)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in fixture file: {e}", file=sys.stderr)
        sys.exit(1)

    # Run test
    result = run_script_test(args.parameter, option_object)

    # Output
    print(format_output(result, verbose=args.verbose))

    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
