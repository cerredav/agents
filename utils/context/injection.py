"""Utilities for collecting and injecting runtime context into model prompts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .rules import DEFAULT_RULES_DIRECTORY, get_rules_context


Context = Mapping[str, Any]
ContextProvider = Callable[[], Context]


def collect_context(*providers: ContextProvider) -> dict[str, Any]:
    """Call context providers and merge their results from left to right."""
    context: dict[str, Any] = {}
    for provider in providers:
        provided = provider()
        if not isinstance(provided, Mapping):
            raise TypeError("Context providers must return a mapping.")
        context.update(provided)
    return context


def inject_context(prompt: str, context: Context, *, heading: str = "Runtime context") -> str:
    """Append structured runtime context to a prompt for model consumption."""
    if not context:
        return prompt
    serialized = json.dumps(dict(context), indent=2, ensure_ascii=False, default=str)
    return f"{prompt.rstrip()}\n\n{heading}:\n{serialized}"


def inject_rules(
    prompt: str,
    context: Context | None = None,
    *,
    rules_directory: str | Path = DEFAULT_RULES_DIRECTORY,
    heading: str = "Runtime context and rules",
) -> str:
    """Inject caller-supplied context and every rule file into ``prompt``.

    Caller-supplied context is retained, except for the reserved ``rules`` key,
    which always reflects the contents of ``rules_directory``.
    """
    combined_context = dict(context or {})
    combined_context.update(get_rules_context(rules_directory))
    return inject_context(prompt, combined_context, heading=heading)
