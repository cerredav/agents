"""Resolve and execute callables declared by YAML tool definitions."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any, Callable

import yaml


TOOLS_DIRECTORY = Path(__file__).parents[1] / "tools"


class ToolExecutionError(RuntimeError):
    """Raised when a tool cannot be resolved, loaded, or executed."""


def run_tool(
    tool_name: str,
    parameters: dict[str, Any] | None = None,
    *,
    tools_directory: str | Path = TOOLS_DIRECTORY,
) -> Any:
    """Load a tool's configured callable and invoke it with ``parameters``."""
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise ToolExecutionError("Tool name must be a non-empty string.")
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise ToolExecutionError("Tool parameters must be a dictionary.")

    directory = Path(tools_directory).resolve()
    definition, definition_path = _find_tool(tool_name.strip(), directory)
    if definition.get("enabled", True) is not True:
        raise ToolExecutionError(
            f"Tool '{tool_name}' is disabled in {definition_path}."
        )
    callable_config = definition.get("callable")

    if not isinstance(callable_config, dict):
        raise ToolExecutionError(
            f"Tool '{tool_name}' does not define a callable in {definition_path}."
        )

    file_name = callable_config.get("file")
    function_name = callable_config.get("function")
    if not isinstance(file_name, str) or not file_name.strip():
        raise ToolExecutionError(f"Tool '{tool_name}' callable requires a file.")
    if not isinstance(function_name, str) or not function_name.strip():
        raise ToolExecutionError(f"Tool '{tool_name}' callable requires a function.")

    _validate_declared_parameters(tool_name, parameters, definition)
    function = _load_callable(
        tool_name=tool_name,
        module_path=_safe_module_path(directory, file_name),
        function_name=function_name,
    )

    try:
        inspect.signature(function).bind(**parameters)
    except TypeError as error:
        raise ToolExecutionError(
            f"Invalid parameters for tool '{tool_name}': {error}"
        ) from error

    try:
        return function(**parameters)
    except Exception as error:
        raise ToolExecutionError(f"Tool '{tool_name}' failed: {error}") from error


def _find_tool(
    tool_name: str, tools_directory: Path
) -> tuple[dict[str, Any], Path]:
    """Recursively find a tool definition by its declared name."""
    if not tools_directory.is_dir():
        raise ToolExecutionError(f"Tools directory does not exist: {tools_directory}")

    for definition_path in sorted(tools_directory.rglob("*.yml")):
        try:
            with definition_path.open("r", encoding="utf-8") as definition_file:
                definition = yaml.safe_load(definition_file)
        except (OSError, yaml.YAMLError) as error:
            raise ToolExecutionError(
                f"Could not read tool definition {definition_path}: {error}"
            ) from error

        if isinstance(definition, dict) and definition.get("name") == tool_name:
            return definition, definition_path

    raise ToolExecutionError(f"Unknown tool: '{tool_name}'.")


def _safe_module_path(tools_directory: Path, file_name: str) -> Path:
    module_path = (tools_directory / file_name).resolve()
    if not module_path.is_relative_to(tools_directory):
        raise ToolExecutionError(
            f"Callable file must be located inside {tools_directory}."
        )
    if not module_path.is_file() or module_path.suffix != ".py":
        raise ToolExecutionError(f"Callable module does not exist: {module_path}")
    return module_path


def _load_callable(
    *, tool_name: str, module_path: Path, function_name: str
) -> Callable[..., Any]:
    module_name = f"_agent_tool_{tool_name}_{abs(hash(module_path))}"
    specification = importlib.util.spec_from_file_location(module_name, module_path)
    if specification is None or specification.loader is None:
        raise ToolExecutionError(f"Could not load callable module: {module_path}")

    module = importlib.util.module_from_spec(specification)
    try:
        specification.loader.exec_module(module)
    except Exception as error:
        raise ToolExecutionError(
            f"Could not import callable module {module_path}: {error}"
        ) from error

    function = getattr(module, function_name, None)
    if not callable(function):
        raise ToolExecutionError(
            f"Function '{function_name}' was not found in {module_path}."
        )
    return function


def _validate_declared_parameters(
    tool_name: str,
    parameters: dict[str, Any],
    definition: dict[str, Any],
) -> None:
    schema = definition.get("parameters")
    if schema is None:
        schema = {}
    if not isinstance(schema, dict):
        raise ToolExecutionError(
            f"Tool '{tool_name}' has an invalid parameters schema."
        )

    null_parameters = sorted(name for name, value in parameters.items() if value is None)
    if null_parameters:
        raise ToolExecutionError(
            f"Null parameter value(s) for tool '{tool_name}': "
            f"{', '.join(null_parameters)}. Omit unknown optional parameters; "
            "required parameters must have concrete values."
        )

    unknown = sorted(set(parameters) - set(schema))
    if unknown:
        raise ToolExecutionError(
            f"Unknown parameter(s) for tool '{tool_name}': {', '.join(unknown)}"
        )

    disabled = sorted(
        name
        for name, parameter_schema in schema.items()
        if name in parameters
        and isinstance(parameter_schema, dict)
        and parameter_schema.get("enabled", True) is not True
    )
    if disabled:
        raise ToolExecutionError(
            f"Disabled parameter(s) for tool '{tool_name}': {', '.join(disabled)}"
        )

    missing = sorted(
        name
        for name, parameter_schema in schema.items()
        if isinstance(parameter_schema, dict)
        and parameter_schema.get("required") is True
        and name not in parameters
    )
    if missing:
        raise ToolExecutionError(
            f"Missing required parameter(s) for tool '{tool_name}': "
            f"{', '.join(missing)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a configured agent tool.")
    parser.add_argument("tool", help="tool name from a YAML definition")
    parser.add_argument(
        "parameters",
        nargs="?",
        default="{}",
        help='parameters as JSON, for example \'{"latitude": 1, "longitude": 2}\'',
    )
    args = parser.parse_args()

    try:
        parameters = json.loads(args.parameters)
        result = run_tool(args.tool, parameters)
    except (json.JSONDecodeError, ToolExecutionError) as error:
        parser.exit(status=1, message=f"error: {error}\n")

    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result)


if __name__ == "__main__":
    main()
