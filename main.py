"""Interactive command-line shell for the weather agent.

The model integration intentionally lives behind ``get_model_response`` so it
can be added later without changing the shell itself.
"""

from __future__ import annotations

from model.repl import AgentShell, ModelResponder, get_model_response

def run_shell(responder: ModelResponder = get_model_response) -> None:
    """Start an interactive weather-agent session."""
    AgentShell(responder=responder).run()


if __name__ == "__main__":
    run_shell()
