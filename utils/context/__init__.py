"""Runtime context providers and prompt injection helpers."""

from .date import get_current_datetime_context
from .injection import collect_context, inject_context
from .rules import DEFAULT_RULES_DIRECTORY, get_rules_context

__all__ = [
    "collect_context",
    "DEFAULT_RULES_DIRECTORY",
    "get_current_datetime_context",
    "get_rules_context",
    "inject",
    "inject_context",
]
