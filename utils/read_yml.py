"""Helpers for reading YAML configuration and prompt response formats."""

from pathlib import Path
from typing import Any

import yaml


def read_yml(file_path: str | Path) -> Any:
    with Path(file_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def read_response_format(prompt_path: str | Path) -> dict[str, Any] | None:
    """Read and validate the response format colocated with a prompt file."""
    path = Path(prompt_path).with_name("response_schema.yml")
    document = read_yml(path)

    if not isinstance(document, dict) or "response_format" not in document:
        raise ValueError(
            f"Prompt response schema must define 'response_format': {path}"
        )

    response_format = document["response_format"]
    if response_format is None:
        return None
    if not isinstance(response_format, dict):
        raise ValueError(f"Invalid response format in {path}")
    if response_format.get("type") != "json_schema":
        raise ValueError(f"Unsupported response format in {path}")

    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, dict) or not isinstance(
        json_schema.get("schema"), dict
    ):
        raise ValueError(f"Response format must contain a JSON schema: {path}")

    return response_format
