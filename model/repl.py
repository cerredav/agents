"""
Small REPL (Read-Eval-Print Loop)that owns the conversation history.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .connection import stream_model_response
from utils.read_yml import read_yml
from utils.write_to_file import write_to_file
from utils.tokenizer import count_tokens

from .react import submit_to_loop 
from .graph import submit_to_graph

import json
import asyncio


Message = dict[str, str]
ModelResponder = Callable[[Sequence[Message]], Iterator[str]]
TokenCount = dict[str, int]
PROMPTS_PATH = Path(__file__).parents[1] / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_PATH / "system" / "prompt.yml"
REACT_PROMPT_PATH = PROMPTS_PATH / "react" / "prompt.yml"

transcript_file = open("transcript.txt", "w")
log_file = open("log.txt", "w")

@dataclass
class AgentShell:
    responder: ModelResponder = lambda message: stream_model_response(message)
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
    def _react_message(user_input: str, context: str) -> Message:
        react_prompt = read_yml(str(REACT_PROMPT_PATH))["react_prompt"]
        return {
            "role": "system",
            "content": react_prompt.format(user_input=user_input, context=context),
        }

    async def run(self) -> None:
        print("Ask about the weather in a location, or type /help for commands.")
        current_token_count: TokenCount = {
            "input": 0,
            "output": 0,
            "reasoning": 0
        }
        context = ''

        # initialize the system prompt
        write_to_file(transcript_file, json.dumps(self.messages[-1], indent=4) + "\n")

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
            write_to_file(transcript_file, json.dumps(self.messages[-1], indent=4) + "\n")

            def onProgress(token_count: dict):
                current_token_count['reasoning'] += token_count['reasoning']

            # submit to react
            context = await submit_to_graph(user_input, onProgress=onProgress)

            # Asking the model to react to the user's input based on the tool result
            log = f"""[MODEL_INSTRUCTION] {self._react_message(user_input=user_input, context=context)["content"]}\n"""
            write_to_file(log_file, log)
            chunks = []
            for chunk in self.responder(tuple([
                self._react_message(user_input=user_input, context=context)
            ])):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            response = "".join(chunks)
            log = f"""[RESPONSE] {response}"""
            write_to_file(log_file, log, end_block=True)
            response_message = {
                "role": "assistant",
                "content": response,
            }
            self.messages.append(response_message)
            write_to_file(transcript_file, json.dumps(response_message, indent=4) + "\n")

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
