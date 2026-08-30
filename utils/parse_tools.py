"""Parse YAML tool definitions for use in the reasoning prompt."""

from __future__ import annotations

import os
import argparse
import json
from pathlib import Path
from typing import Any

import yaml


TOOLS_DIRECTORY = Path(__file__).parents[1] / "tools"


class ToolParseError(ValueError):
    """Raised when a tool definition is missing or malformed."""


def parse_tools(tools_directory: str | Path = TOOLS_DIRECTORY, capability: str | None = None) -> list[dict[str, Any]]:
    """Recursively read and normalize every ``.yml`` tool definition.

    Tools are ordered by name so the resulting prompt remains deterministic.
    """
    directory = Path(tools_directory)
    if not directory.is_dir():
        raise ToolParseError(f"Tools directory does not exist: {directory}")

    tools: list[dict[str, Any]] = []
    if capability:
        if os.path.isdir(directory / capability):
            tools = parse_tools(directory / capability)
        else:
            tool = _parse_tool(directory / f"{capability}.yml")
            if tool:
                tools.append(tool)
    else:
        for tool_path in sorted(directory.rglob("*.yml")):
            tool = _parse_tool(tool_path)
            if tool:
                tools.append(tool)

    if not tools:
        raise ToolParseError(
            f"No .yml tool definitions found in {directory} or its subdirectories"
        )

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

    if definition.get("enabled", True) is not True:
        return {}

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
        if specification.get("enabled", True) is True:
            normalized_parameters[parameter_name] = specification

    return {
        "name": definition["name"].strip(),
        "description": definition["description"].strip(),
        "parameters": normalized_parameters,
    }


def format_tools_for_prompt(
    tools_directory: str | Path = TOOLS_DIRECTORY,
    *,
    capability: str | None = None
) -> str:
    """Return tool definitions as readable JSON for ``reasoning.yml``."""
    return json.dumps(
        parse_tools(tools_directory, capability), indent=2, ensure_ascii=False
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse YAML tool definitions into prompt-ready JSON."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=TOOLS_DIRECTORY,
        help=(
            "directory recursively containing tool YAML files "
            f"(default: {TOOLS_DIRECTORY})"
        ),
    )
    args = parser.parse_args()

    try:
        print(format_tools_for_prompt(args.directory))
    except ToolParseError as error:
        parser.exit(status=1, message=f"error: {error}\n")


if __name__ == "__main__":
    main()
