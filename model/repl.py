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
    responder: ModelResponder
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

            # get the user's intent
            intent_message = self._intent_message()
            intent_message_array = [
                self._intent_message(),
                user_message
            ]
            log = f"""[USER_INPUT] {user_input}\n[TODLER_INSTRUCTION] {intent_message["content"]}\n"""
            write_to_log(log)
            chunks = []
            for chunk in self.responder(tuple(intent_message_array)):
                chunks.append(chunk)
                print(chunk, end="", flush=True)

            intent_response = "".join(chunks)
            log = f"""[RESPONSE]{intent_response}"""
            write_to_log(log, end_block=True)
            intent_response_tokens = count_tokens(intent_response)
            current_token_count["reasoning"] += intent_response_tokens

            def think(users_intent: str, context: str) -> tuple[str, str, str, str]:
                print('\n----------------------------------------------------------------')
                print('Planning the next best course of action...')
                print('----------------------------------------------------------------\n')
                # plan the next best course of action
                planner_message = self._planner_message(user_intent=users_intent, context=context)
                log = f"""[TODLER_INSTRUCTION] {planner_message["content"]}\n"""
                write_to_log(log)
                chunks = []
                for chunk in self.responder(tuple([planner_message])):
                    chunks.append(chunk)
                    print(chunk, end="", flush=True)
                planner_response = "".join(chunks)
                log = f"""[RESPONSE] {planner_response}"""
                write_to_log(log, end_block=True)
                current_token_count["reasoning"] += count_tokens(planner_response)
                print('\n----------------------------------------------------------------')
                print('Reasoning about the next best course of action...')
                print('----------------------------------------------------------------\n')

                # get the best tool to use
                reasoning_message = self._reasoning_message(plan=planner_response, context=context)
                log = f"""[TODLER_INSTRUCTION] {reasoning_message["content"]}\n"""
                write_to_log(log)
                chunks = []
                for chunk in self.responder(tuple([reasoning_message])):
                    chunks.append(chunk)

                reasoning_response = "".join(chunks)
                log = f"""[RESPONSE] {reasoning_response}"""
                write_to_log(log, end_block=True)
                current_token_count["reasoning"] += count_tokens(reasoning_response)

                try:
                    # parse the reasoning response
                    reasoning_response = json.loads(reasoning_response)
                except Exception as error:
                    print("\n[ERROR] Error parsing reasoning response")
                    print(f"[ERROR] Error: {error}", end="", flush=True)
                    print(f"\n[ERROR] Reasoning response: {reasoning_response}", end="", flush=True)
                    reasoning_response = {}
                    return reasoning_response, None, None, None

                print('\n----------------------------------------------------------------')
                print('Using the tool...')
                print('----------------------------------------------------------------\n')

                # use the tool
                print(f'\n[INFO] Reasoning response: {reasoning_response}')
                tool_name = reasoning_response.get("tool", None)
                tool_parameters = reasoning_response.get("parameters", None)

                # if tool is empty
                result = None
                if tool_name is None and tool_parameters is None:
                    print(f"\n[INFO] No tool to use")
                    return reasoning_response, None, None, None
                else:
                    print(f"\n[INFO] Tool name: {tool_name}\n")
                    print(f"\n[INFO] Tool parameters: {tool_parameters}\n")
                    print()
                    try:
                        result = run_tool(tool_name, tool_parameters)
                    except Exception as error:
                        print(f"\n[ERROR] Error running tool: {error}")
                    print(f"\n[INFO] Result: {result}", end="", flush=True)

                # add the reasoning response to the messages
                log = f"""[TOOL_USED] {tool_name}\n[TOOL_PARAMETERS] {tool_parameters}\n[RESULT] {result}"""
                write_to_log(log, end_block=True)

                print('\n----------------------------------------------------------------')
                print('Completed the task!')
                print('----------------------------------------------------------------')

                return reasoning_response, tool_name, tool_parameters, result


            has_completed = False
            context = ''

            while not has_completed:
                # think and act
                reasoning_response, tool_name, tool_parameters, result = think(intent_response, context=context)
                context += f"[TOOL_RESULT] {result}\n"
                observe_message = self._observe_message(context=context, user_request=user_input)

                print('----------------------------------------------------------------')
                print('Observing the tool result...')
                print('----------------------------------------------------------------\n')

                loop_response = ""
                loop_chunks = []
                print()
                log = f"""[TODLER_INSTRUCTION] {observe_message["content"]}\n"""
                write_to_log(log)
                # observe
                for chunk in self.responder(tuple([observe_message])):
                    loop_chunks.append(chunk)
                    print(chunk, end="", flush=True)

                log = f"""[RESPONSE] {loop_response}"""
                write_to_log(log, end_block=True)

                # parse the loop response
                loop_response = "".join(loop_chunks)
                loop_response_tokens = count_tokens(loop_response)
                current_token_count["reasoning"] += loop_response_tokens
                try:
                    loop_response = loop_response.strip()
                    print(f'\n[INFO] Loop response: {loop_response}')
                    has_completed = loop_response.strip().lower() == "true"
                    print(f'[INFO] Has completed: {has_completed}')
                except Exception as error:
                    print(f'\n[ERROR] Error parsing loop response: {error}')
                    print(f'\n[ERROR] Loop response: {loop_response}')
                    loop_response = False
                    has_completed = False


            # Asking the todler to react to the user's input based on the tool result
            log = f"""[TODLER_INSTRUCTION] {self._react_message(user_input=user_input, context=context)["content"]}\n"""
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
