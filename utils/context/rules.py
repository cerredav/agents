"""Rule-file context for model prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_RULES_DIRECTORY = Path(__file__).resolve().parents[2] / "rules"


def get_rules_context(
    rules_directory: str | Path = DEFAULT_RULES_DIRECTORY,
) -> dict[str, Any]:
    """Read every file under ``rules_directory`` as prompt context.

    Rules are sorted by their relative path so prompt construction is stable
    across operating systems and runs.
    """
    directory = Path(rules_directory)
    if not directory.exists():
        raise FileNotFoundError(f"Rules directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Rules path is not a directory: {directory}")

    rules = []
    for path in sorted(
        (candidate for candidate in directory.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(directory).as_posix(),
    ):
        content = path.read_text(encoding="utf-8").strip()
        rules.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "content": content,
            }
        )

    return {"rules": rules}
