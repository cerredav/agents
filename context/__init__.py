"""Runtime context providers and prompt injection helpers."""

from .date import get_current_datetime_context
from .injection import collect_context, inject_context

__all__ = [
    "collect_context",
    "get_current_datetime_context",
    "inject_context",
]
