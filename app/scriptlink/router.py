"""Script router for runtime discovery and execution."""
import importlib.util
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.scriptlink.option_object import OptionObjectWrapper

logger = logging.getLogger(__name__)

# Type alias for script handler function
ScriptHandler = Callable[["OptionObjectWrapper"], None]

# Allow alphanumerics, underscores, hyphens, spaces, and dots (for field-style names)
_SAFE_PARAMETER = re.compile(r'^[A-Za-z0-9_\- .]+$')


class ScriptRouter:
    """Discovers and routes to scripts by parameter name at runtime.

    Scripts are Python files in the scripts/ directory.
    The filename (without .py) becomes the parameter name.

    Example:
        router = ScriptRouter(Path("scripts"), Path("data"))

        # Get handler for a parameter
        handler = router.get_handler("ADMIT_VALIDATION")
        if handler:
            handler(option_object)
        else:
            router.save_missing_script_data("ADMIT_VALIDATION", option_object.to_dict())
    """

    def __init__(self, scripts_dir: Path, data_dir: Path):
        """Initialize the script router.

        Args:
            scripts_dir: Directory containing script files
            data_dir: Directory for data files (missing script dumps)
        """
        self.scripts_dir = scripts_dir
        self.data_dir = data_dir
        self.missing_scripts_dir = data_dir / "missing_scripts"
        self.max_fixtures_per_parameter = 3

    def get_handler(self, parameter: str) -> Optional[ScriptHandler]:
        """Get the handler function for a parameter.

        Loads the script fresh on each call (no caching) to support
        live editing during development.

        Args:
            parameter: The ScriptLink parameter name

        Returns:
            The script's run() function or None if not found
        """
        if not _SAFE_PARAMETER.match(parameter):
            logger.warning("Rejected invalid parameter name: %r", parameter)
            return None

        script_path = self.scripts_dir / f"{parameter}.py"

        if not script_path.resolve().is_relative_to(self.scripts_dir.resolve()):
            logger.warning("Rejected path traversal in parameter: %r", parameter)
            return None

        if not script_path.exists():
            return None

        return self._load_script(script_path, parameter)

    def _load_script(self, path: Path, parameter: str) -> ScriptHandler:
        """Load a script module and extract the handler function.

        Args:
            path: Path to the script file
            parameter: The parameter name (used as module name)

        Returns:
            The run() function from the script

        Raises:
            RuntimeError: If the script cannot be loaded or has no run() function
        """
        # Create a unique module name to avoid conflicts
        module_name = f"scripts.{parameter}"

        # Evict the entry script and any helper modules under the scripts
        # package so live edits to shared helpers are picked up too, not just
        # the entry script. Build the list first to avoid mutating while iterating.
        for cached in [
            name for name in sys.modules
            if name == "scripts" or name.startswith("scripts.")
        ]:
            del sys.modules[cached]

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to create module spec for script: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Look for 'run' function
        if hasattr(module, "run") and callable(module.run):
            return module.run

        raise RuntimeError(f"Script {path} has no 'run' function")

    def save_missing_script_data(self, parameter: str, option_object_dict: dict) -> Optional[Path]:
        """Save OptionObject data for developing a missing script.

        When a parameter is called but no script exists, this saves the
        incoming data as JSON so developers can understand the structure.

        Args:
            parameter: The missing script parameter
            option_object_dict: The OptionObject as a dictionary

        Returns:
            Path to the saved file, or None if parameter name is invalid
        """
        if not _SAFE_PARAMETER.match(parameter):
            logger.warning("Rejected invalid parameter name for fixture save: %r", parameter)
            return None

        self.missing_scripts_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{parameter}_{timestamp}.json"
        path = self.missing_scripts_dir / filename

        with open(path, "w") as f:
            json.dump(option_object_dict, f, indent=2)

        logger.info(f"Saved missing script data: {path}")
        self._rotate_fixtures(parameter)
        return path

    def _rotate_fixtures(self, parameter: str) -> None:
        """Keep only the most recent fixtures for a parameter.

        Prevents unbounded disk growth when an unknown parameter is called
        repeatedly. Timestamps are in the filename, so lexicographic sort
        matches chronological order.
        """
        existing = sorted(self.missing_scripts_dir.glob(f"{parameter}_*.json"))
        for stale in existing[:-self.max_fixtures_per_parameter]:
            try:
                stale.unlink()
            except OSError:
                logger.warning("Failed to remove stale fixture: %s", stale, exc_info=True)

    def list_scripts(self) -> list[str]:
        """List all available script parameters.

        Returns:
            List of parameter names (script filenames without .py)
        """
        if not self.scripts_dir.exists():
            return []

        return [
            p.stem for p in self.scripts_dir.glob("*.py")
            if not p.name.startswith("_")
        ]

    def script_exists(self, parameter: str) -> bool:
        """Check if a script exists for a parameter.

        Args:
            parameter: The parameter name to check

        Returns:
            True if script file exists
        """
        return (self.scripts_dir / f"{parameter}.py").exists()
