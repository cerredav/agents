"""Parse YAML tool definitions for use in the reasoning prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


TOOLS_DIRECTORY = Path(__file__).parents[1] / "tools"


class ToolParseError(ValueError):
    """Raised when a tool definition is missing or malformed."""


def parse_tools(tools_directory: str | Path = TOOLS_DIRECTORY) -> list[dict[str, Any]]:
    """Read and normalize every ``.yml`` tool definition in a directory.

    Tools are ordered by name so the resulting prompt remains deterministic.
    """
    directory = Path(tools_directory)
    if not directory.is_dir():
        raise ToolParseError(f"Tools directory does not exist: {directory}")

    tools: list[dict[str, Any]] = []
    for tool_path in sorted(directory.glob("*.yml")):
        tools.append(_parse_tool(tool_path))

    if not tools:
        raise ToolParseError(f"No .yml tool definitions found in {directory}")

    names = [tool["name"] for tool in tools]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ToolParseError(f"Duplicate tool name(s): {', '.join(duplicates)}")

    return sorted(tools, key=lambda tool: tool["name"])


def _parse_tool(tool_path: Path) -> dict[str, Any]:
    try:
        with tool_path.open("r", encoding="utf-8") as tool_file:
            definition = yaml.safe_load(tool_file)
    except (OSError, yaml.YAMLError) as error:
        raise ToolParseError(f"Could not parse {tool_path}: {error}") from error

    if not isinstance(definition, dict):
        raise ToolParseError(f"{tool_path} must contain a YAML mapping")

    for field in ("name", "description"):
        if not isinstance(definition.get(field), str) or not definition[field].strip():
            raise ToolParseError(f"{tool_path} requires a non-empty '{field}' field")

    parameters = definition.get("parameters")
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise ToolParseError(f"{tool_path} field 'parameters' must be a mapping or null")

    normalized_parameters: dict[str, dict[str, Any]] = {}
    for parameter_name, specification in parameters.items():
        if not isinstance(parameter_name, str) or not isinstance(specification, dict):
            raise ToolParseError(
                f"{tool_path} contains an invalid parameter definition"
            )
        normalized_parameters[parameter_name] = specification

    return {
        "name": definition["name"].strip(),
        "description": definition["description"].strip(),
        "parameters": normalized_parameters,
    }


def format_tools_for_prompt(
    tools_directory: str | Path = TOOLS_DIRECTORY,
) -> str:
    """Return tool definitions as readable JSON for ``reasoning.yml``."""
    return json.dumps(parse_tools(tools_directory), indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse YAML tool definitions into prompt-ready JSON."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=TOOLS_DIRECTORY,
        help=f"directory containing tool YAML files (default: {TOOLS_DIRECTORY})",
    )
    args = parser.parse_args()

    try:
        print(format_tools_for_prompt(args.directory))
    except ToolParseError as error:
        parser.exit(status=1, message=f"error: {error}\n")


if __name__ == "__main__":
    main()
