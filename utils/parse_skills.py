"""Parse YAML skill definitions for use in model prompts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


SKILLS_DIRECTORY = Path(__file__).parents[1] / "skills"


class SkillParseError(ValueError):
    """Raised when a skill definition is missing or malformed."""


def parse_skills(
    skills_directory: str | Path = SKILLS_DIRECTORY,
    skill: str | None = None,
) -> list[dict[str, Any]]:
    """Recursively read and validate skill definitions.

    Skills are sorted by name so the resulting prompt remains deterministic.
    When ``skill`` is supplied, it may identify either a nested directory or a
    YAML filename (with or without the ``.yml`` suffix).
    """
    directory = Path(skills_directory)
    if not directory.is_dir():
        raise SkillParseError(f"Skills directory does not exist: {directory}")

    if skill:
        selected_path = directory / skill
        if selected_path.is_dir():
            skill_paths = sorted(selected_path.rglob("*.yml"))
        else:
            if selected_path.suffix != ".yml":
                selected_path = selected_path.with_suffix(".yml")
            skill_paths = [selected_path]
    else:
        skill_paths = sorted(directory.rglob("*.yml"))

    skills = []
    for skill_path in skill_paths:
        parsed_skill = _parse_skill(skill_path)
        if parsed_skill:
            skills.append(parsed_skill)

    if not skills:
        scope = f" for '{skill}'" if skill else ""
        raise SkillParseError(
            f"No enabled .yml skill definitions found in {directory}{scope}"
        )

    names = [parsed_skill["name"] for parsed_skill in skills]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise SkillParseError(f"Duplicate skill name(s): {', '.join(duplicates)}")

    return sorted(skills, key=lambda parsed_skill: parsed_skill["name"])


def _parse_skill(skill_path: Path) -> dict[str, Any]:
    try:
        with skill_path.open("r", encoding="utf-8") as skill_file:
            definition = yaml.safe_load(skill_file)
    except (OSError, yaml.YAMLError) as error:
        raise SkillParseError(f"Could not parse {skill_path}: {error}") from error

    if not isinstance(definition, dict):
        raise SkillParseError(f"{skill_path} must contain a YAML mapping")
    if definition.get("enabled", True) is not True:
        return {}

    for field in ("name", "description"):
        if not isinstance(definition.get(field), str) or not definition[field].strip():
            raise SkillParseError(
                f"{skill_path} requires a non-empty '{field}' field"
            )

    activation = definition.get("activation")
    if not isinstance(activation, dict):
        raise SkillParseError(
            f"{skill_path} requires an 'activation' mapping"
        )
    use_when = activation.get("use_when")
    if not isinstance(use_when, str) or not use_when.strip():
        raise SkillParseError(
            f"{skill_path} activation requires a non-empty 'use_when' rule"
        )
    skip_when = activation.get("skip_when")
    if skip_when is not None and (
        not isinstance(skip_when, str) or not skip_when.strip()
    ):
        raise SkillParseError(
            f"{skill_path} activation 'skip_when' must be a non-empty string"
        )
    normalized_activation = {
        "use_when": use_when.strip(),
    }
    if skip_when is not None:
        normalized_activation["skip_when"] = skip_when.strip()

    inputs = definition.get("inputs", {})
    if not isinstance(inputs, dict):
        raise SkillParseError(f"{skill_path} field 'inputs' must be a mapping")
    normalized_inputs: dict[str, dict[str, Any]] = {}
    for input_name, specification in inputs.items():
        if not isinstance(input_name, str) or not isinstance(specification, dict):
            raise SkillParseError(f"{skill_path} contains an invalid input definition")
        if specification.get("enabled", True) is True:
            normalized_inputs[input_name] = specification

    tools = definition.get("tools", {})
    if not isinstance(tools, dict) or any(
        not isinstance(alias, str) or not isinstance(tool_name, str)
        for alias, tool_name in tools.items()
    ):
        raise SkillParseError(
            f"{skill_path} field 'tools' must map aliases to tool names"
        )

    workflow = definition.get("workflow")
    if not isinstance(workflow, list) or not workflow:
        raise SkillParseError(
            f"{skill_path} requires a non-empty 'workflow' list"
        )
    step_ids: list[str] = []
    for index, step in enumerate(workflow):
        if not isinstance(step, dict):
            raise SkillParseError(
                f"{skill_path} workflow step {index + 1} must be a mapping"
            )
        for field in ("id", "action"):
            if not isinstance(step.get(field), str) or not step[field].strip():
                raise SkillParseError(
                    f"{skill_path} workflow step {index + 1} requires "
                    f"a non-empty '{field}' field"
                )
        step_ids.append(step["id"])

    duplicate_steps = sorted(
        {step_id for step_id in step_ids if step_ids.count(step_id) > 1}
    )
    if duplicate_steps:
        raise SkillParseError(
            f"{skill_path} contains duplicate workflow step id(s): "
            f"{', '.join(duplicate_steps)}"
        )

    normalized = dict(definition)
    normalized.pop("enabled", None)
    normalized["name"] = definition["name"].strip()
    normalized["description"] = definition["description"].strip()
    normalized["activation"] = normalized_activation
    normalized["inputs"] = normalized_inputs
    normalized["tools"] = tools
    normalized["workflow"] = workflow
    return normalized


def format_skills_for_prompt(
    skills_directory: str | Path = SKILLS_DIRECTORY,
    *,
    skill: str | None = None,
) -> str:
    """Return skill definitions as readable JSON for a model prompt."""
    return json.dumps(
        parse_skills(skills_directory, skill),
        indent=2,
        ensure_ascii=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse YAML skill definitions into prompt-ready JSON."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=SKILLS_DIRECTORY,
        help=(
            "directory recursively containing skill YAML files "
            f"(default: {SKILLS_DIRECTORY})"
        ),
    )
    parser.add_argument(
        "--skill",
        help="optional skill filename or nested skill directory to select",
    )
    args = parser.parse_args()

    try:
        print(format_skills_for_prompt(args.directory, skill=args.skill))
    except SkillParseError as error:
        parser.exit(status=1, message=f"error: {error}\n")


if __name__ == "__main__":
    main()
