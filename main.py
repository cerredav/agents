"""Interactive command-line shell for the weather agent.

The model integration intentionally lives behind ``get_model_response`` so it
can be added later without changing the shell itself.
"""

from __future__ import annotations

from model.repl import AgentShell

def run_shell() -> None:
    """Start an interactive weather-agent session."""
    AgentShell().run()


if __name__ == "__main__":
    run_shell()
