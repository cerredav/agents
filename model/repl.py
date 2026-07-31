"""
Small REPL (Read-Eval-Print Loop)that owns the conversation history.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from .connection import stream_model_response
from utils.read_yml import read_yml
from utils.parse_tools import format_tools_for_prompt
from utils.run_tool import run_tool

import os
import json


Message = dict[str, str]
ModelResponder = Callable[[Sequence[Message]], Iterator[str]]
SYSTEM_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "system.yml"
INTENT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "intent.yml"
REASONING_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "reasoning.yml"

def get_model_response(messages: Sequence[Message]) -> Iterator[str]:
    """Stream the model's response for the current conversation."""
    return stream_model_response(messages)

@dataclass
class AgentShell:
    responder: ModelResponder

    def __post_init__(self) -> None:
        self.messages: list[Message] = [self._system_message()]

    @staticmethod
    def _system_message() -> Message:
        system_prompt = read_yml(str(SYSTEM_PROMPT_PATH))["system_prompt"]
        # add list_tools tool to the system prompt
        return {
            "role": "system",
            "content": system_prompt,
        }
    
    @staticmethod
    def _intent_message() -> Message:
        intent_prompt = read_yml(str(INTENT_PROMPT_PATH))["intent_prompt"]
        return {
            "role": "system",
            "content": intent_prompt,
        }

    @staticmethod
    def _reasoning_message(user_intent: str) -> Message:
        reasoning_prompt = read_yml(str(REASONING_PROMPT_PATH))["reasoning_prompt"]
        system_tools = format_tools_for_prompt()
        return {
            "role": "system",
            "content": reasoning_prompt.format(user_intent=user_intent, system_tools=system_tools),
        }

    def run(self) -> None:
        print("Weather Agent")
        print("Ask about the weather in a location, or type /help for commands.")

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                return

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    return
                continue
        
            def think(user_input: str) -> tuple[str, str, str, str, str]:
                # get the user's intent
                intent_chunks = []
                reasoning_chunks = []
                intent_message = [
                    self._intent_message(),
                    {"role": "user", "content": user_input}
                ]
                intent_response = ""
                reasoning_response = ""
                for chunk in self.responder(tuple(intent_message)):
                    intent_chunks.append(chunk)
                    print(chunk, end="", flush=True)

                intent_response = "".join(intent_chunks)

                # get the best tool to use
                reasoning_message = [
                    self._reasoning_message(intent_response),
                ]
                for chunk in self.responder(tuple(reasoning_message)):
                    reasoning_chunks.append(chunk)

                reasoning_response = "".join(reasoning_chunks)
                try:
                    # parse the reasoning response
                    reasoning_response = json.loads(reasoning_response)
                except Exception as error:
                    print(f"\n[ERROR] Error parsing reasoning response: {error}")
                    reasoning_response = {}
                    return intent_response, reasoning_response, None, None, None

                # use the tool
                tool_name = reasoning_response.get("tool", None)
                tool_parameters = reasoning_response.get("parameters", None)

                # if tool is empty
                result = None
                if tool_name is None and tool_parameters is None:
                    print(f"\n[INFO] No tool to use")
                    return intent_response, reasoning_response, None, None, None
                else:
                    print(f"\n[INFO] Tool name: {tool_name}")
                    print(f"\n[INFO] Tool parameters: {tool_parameters}")
                    try:
                        result = run_tool(tool_name, tool_parameters)
                    except Exception as error:
                        print(f"\n[ERROR] Error running tool: {error}")
                    print(f"\n[INFO] Result: {result}")
                return intent_response, reasoning_response, tool_name, tool_parameters, result


            intent_response, reasoning_response, tool_name, tool_parameters, result = think(user_input)
            # create user message with the tool result
            content = f"""
            User Input: {user_input}
            Deicphered Intent: {intent_response}
            Available Tools: {reasoning_response}
            Used Tool: {tool_name}
            Tool Parameters: {tool_parameters}
            Tool Result: {result}
            """
            user_message = {
                "role": "user",
                "content": content,
            }
            self.messages.append(user_message)

            chunks = []
            for chunk in self.responder(tuple(self.messages)):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            response = "".join(chunks)

            self.messages.append({"role": "assistant", "content": response})

    def _handle_command(self, command: str) -> bool:
        normalized = command.lower()

        if normalized in {"/exit", "/quit"}:
            print("Goodbye!")
            return False

        if normalized == "/help":
            print(
                "Commands:\n"
                "  /help     Show this help message\n"
                "  /clear    Start a new conversation\n"
                "  /history  Show the current conversation\n"
                "  /exit     Leave the shell"
            )
            return True

        if normalized == "/clear":
            self.messages = [self._system_message()]
            print("Conversation cleared.")
            return True

        if normalized == "/history":
            conversation = [
                message for message in self.messages if message["role"] != "system"
            ]
            if not conversation:
                print("No conversation history yet.")
            else:
                for message in conversation:
                    label = "You" if message["role"] == "user" else "Agent"
                    print(f"{label}: {message['content']}")
            return True

        print(f"Unknown command: {command}. Type /help for available commands.")
        return True
