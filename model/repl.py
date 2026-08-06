"""
Small REPL (Read-Eval-Print Loop)that owns the conversation history.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .connection import stream_model_response
from utils.read_yml import read_yml
from utils.parse_tools import format_tools_for_prompt
from utils.run_tool import run_tool
from utils.tokenizer import count_tokens

from .react import submit_to_loop 

import os
import json


Message = dict[str, str]
ModelResponder = Callable[[Sequence[Message]], Iterator[str]]
TokenCount = dict[str, int]
SYSTEM_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "system.yml"
INTENT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "intent.yml"
REASONING_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "reasoning.yml"
LOOP_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "loop.yml"
PLANNER_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "planner.yml"
OBSERVE_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "observe.yml"
REACT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "react.yml"

transcript = open("transcript.txt", "w")
log = open("log.txt", "w")

def write_to_log(message: str, end_block: bool = False) -> None:
    log.write(message)
    if end_block:
        log.write("\n" + "-"*80 + "\n")
    log.flush()

def close_log() -> None:
    log.close()

def write_to_transcript(message: str) -> None:
    transcript.write(message)
    transcript.flush()

def close_transcript() -> None:
    transcript.close()

def get_model_response(messages: Sequence[Message]) -> Iterator[str]:
    """Stream the model's response for the current conversation."""
    return stream_model_response(messages)

@dataclass
class AgentShell:
    responder: ModelResponder = lambda message: get_model_response(message)
    token_count: TokenCount = field(default_factory=lambda: {
        "input": 0,
        "output": 0,
        "reasoning": 0
    })

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
    def _planner_message(user_intent: str, context: str) -> Message:
        planner_prompt = read_yml(str(PLANNER_PROMPT_PATH))["planner_prompt"]
        return {
            "role": "system",
            "content": planner_prompt.format(user_intent=user_intent, context=context),
        }

    @staticmethod
    def _reasoning_message(plan: str, context: str) -> Message:
        reasoning_prompt = read_yml(str(REASONING_PROMPT_PATH))["reasoning_prompt"]
        system_tools = format_tools_for_prompt()
        return {
            "role": "system",
            "content": reasoning_prompt.format(plan=plan, system_tools=system_tools, context=context),
        }
    
    @staticmethod
    def _observe_message(context: str, user_request: str) -> Message:
        observe_prompt = read_yml(str(OBSERVE_PROMPT_PATH))["observe_prompt"]
        return {
            "role": "system",
            "content": observe_prompt.format(context=context, user_request=user_request),
        }
    
    @staticmethod
    def _react_message(user_input: str, context: str) -> Message:
        react_prompt = read_yml(str(REACT_PROMPT_PATH))["react_prompt"]
        return {
            "role": "system",
            "content": react_prompt.format(user_input=user_input, context=context),
        }

    def run(self) -> None:
        print("Weather Agent")
        print("Ask about the weather in a location, or type /help for commands.")
        current_token_count: TokenCount = {
            "input": 0,
            "output": 0,
            "reasoning": 0
        }
        context = ''

        # initialize the system prompt
        write_to_transcript(json.dumps(self.messages[-1], indent=4) + "\n")

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

            # tokenize the user's input
            user_input_tokens = count_tokens(user_input)    
            current_token_count["input"] += user_input_tokens
        
            # Add the user's input to the messages
            user_message = {
                "role": "user",
                "content": user_input,
            }
            self.messages.append(user_message)
            write_to_transcript(json.dumps(self.messages[-1], indent=4) + "\n")

            def onProgress(token_count: dict):
                current_token_count['reasoning'] += token_count['reasoning']

            # submit to react
            context = submit_to_loop(user_input, onProgress=onProgress)

            # Asking the model to react to the user's input based on the tool result
            log = f"""[MODEL_INSTRUCTION] {self._react_message(user_input=user_input, context=context)["content"]}\n"""
            write_to_log(log)
            chunks = []
            for chunk in self.responder(tuple([
                self._react_message(user_input=user_input, context=context)
            ])):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            response = "".join(chunks)
            log = f"""[RESPONSE] {response}"""
            write_to_log(log, end_block=True)
            response_message = {
                "role": "assistant",
                "content": response,
            }
            self.messages.append(response_message)
            write_to_transcript(json.dumps(response_message, indent=4) + "\n")

            response_tokens = count_tokens(response)
            current_token_count["output"] += response_tokens

            self.token_count["input"] += current_token_count["input"]
            self.token_count["output"] += current_token_count["output"]
            self.token_count["reasoning"] += current_token_count["reasoning"]

            print(f"\n[INFO] Running total token count: {self.token_count}")


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
