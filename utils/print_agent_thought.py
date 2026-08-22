"""Render agent thoughts in a distinctive console panel."""

from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def print_agent_thought(
    thought: Any,
    *,
    title: str = "Agent thought",
    style: str = "cyan",
    console: Console | None = None,
) -> None:
    """Print any value as a labeled, multiline-friendly console panel.

    Args:
        thought: Value to display. Non-string values are converted with ``str``.
        title: Label displayed in the panel border.
        style: Rich style used for the panel border and title.
        console: Optional Rich console, useful for testing or custom output.
    """
    output = console or Console()
    content = Text(str(thought), overflow="fold")
    output.print(
        Panel(
            content,
            title=f"[bold]{title}[/bold]",
            title_align="left",
            border_style=style,
            padding=(0, 1),
        )
    )


def make_agent_thought_callback(
    *,
    title: str = "Model thinking",
    style: str = "yellow",
    console: Console | None = None,
    on_thought: Callable[[str], None] | None = None,
) -> Callable[[str], None]:
    """Create a callback that renders and optionally records model thinking."""

    def on_thinking(thought: str) -> None:
        if thought.strip():
            print_agent_thought(
                thought,
                title=title,
                style=style,
                console=console,
            )
            if on_thought is not None:
                on_thought(thought)

    return on_thinking
