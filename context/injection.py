"""Utilities for collecting and injecting runtime context into model prompts."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any


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
