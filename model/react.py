from pathlib import Path
from collections.abc import Callable

from .connection import stream_model_response
from utils.tokenizer import count_tokens
from utils.write_to_file import write_to_file
from utils.read_yml import read_yml
from utils.parse_tools import format_tools_for_prompt
from utils.run_tool import run_tool

import json

Message = dict[str, str]
TokenCount = dict[str, int]

transcript_file = open("transcript_loop.txt", "w")
log_file = open("log_loop.txt", "w")
token_count: TokenCount = {
    "input": 0,
    "output": 0,
    "reasoning": 0
}

SYSTEM_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "system.yml"
INTENT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "intent.yml"
REASONING_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "reasoning.yml"
LOOP_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "loop.yml"
PLANNER_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "planner.yml"
OBSERVE_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "observe.yml"
REACT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "react.yml"

def _intent_message() -> Message:
    intent_prompt = read_yml(str(INTENT_PROMPT_PATH))["intent_prompt"]
    return {
        "role": "system",
        "content": intent_prompt,
    }

def _planner_message(user_intent: str, context: str) -> Message:
    planner_prompt = read_yml(str(PLANNER_PROMPT_PATH))["planner_prompt"]
    return {
        "role": "system",
        "content": planner_prompt.format(user_intent=user_intent, context=context),
    }

def _reasoning_message(plan: str, context: str) -> Message:
    reasoning_prompt = read_yml(str(REASONING_PROMPT_PATH))["reasoning_prompt"]
    system_tools = format_tools_for_prompt()
    return {
        "role": "system",
        "content": reasoning_prompt.format(plan=plan, system_tools=system_tools, context=context),
    }

def _observe_message(context: str, user_request: str) -> Message:
    observe_prompt = read_yml(str(OBSERVE_PROMPT_PATH))["observe_prompt"]
    return {
        "role": "system",
        "content": observe_prompt.format(context=context, user_request=user_request),
    }

def submit_to_loop(user_input: str, onProgress: Callable | None = None):
    """
    Accept a user input and start the loop
    """
    has_completed = False
    context = ''
    # Add the user's input to the messages
    user_message = {
        "role": "user",
        "content": user_input,
    }
    # decipher a user's intent
    intent_message = _intent_message()
    intent_message_array = [
        _intent_message(),
        user_message
    ]
    log = f"""[USER_INPUT] {user_input}\n[MODEL_INSTRUCTION] {intent_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(tuple(intent_message_array)):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    intent_response = "".join(chunks)
    log = f"""[RESPONSE]{intent_response}"""
    write_to_file(log_file, log, end_block=True)
    intent_response_tokens = count_tokens(intent_response)
    token_count["reasoning"] += intent_response_tokens
    # callback
    onProgress(token_count)


    # start loop until the model finishes.
    # finishing rule is to have has_completed=True
    while not has_completed:
        # think and act
        result = think(intent_response, context=context, onProgress=onProgress)
        context += f"[TOOL_RESULT] {result}\n"
        observe_message = _observe_message(context=context, user_request=user_input)

        print('----------------------------------------------------------------')
        print('Observing the tool result...')
        print('----------------------------------------------------------------\n')

        loop_response = ""
        loop_chunks = []
        print()
        log = f"""[MODEL_INSTRUCTION] {observe_message["content"]}\n"""
        write_to_file(log_file, log)
        # observe
        for chunk in stream_model_response(tuple([observe_message])):
            loop_chunks.append(chunk)

        log = f"""[RESPONSE] {loop_response}"""
        write_to_file(log_file, log, end_block=True)

        # parse the loop response
        loop_response = "".join(loop_chunks)
        loop_response_tokens = count_tokens(loop_response)
        token_count["reasoning"] += loop_response_tokens
        # callback
        onProgress(token_count)
        try:
            loop_response = loop_response.strip()
            has_completed = loop_response.strip().lower() == "true"
            print(f'[INFO] Has completed: {has_completed}')
        except Exception as error:
            print(f'\n[ERROR] Error parsing loop response: {error}')
            print(f'\n[ERROR] Loop response: {loop_response}')
            loop_response = False
            has_completed = False

    return context

def think(users_intent: str, context: str, onProgress: Callable) -> tuple[str, str, str, str]:
    print('\n----------------------------------------------------------------')
    print('Planning the next best course of action...')
    print('----------------------------------------------------------------\n')
    # plan the next best course of action
    planner_message = _planner_message(user_intent=users_intent, context=context)
    log = f"""[MODEL_INSTRUCTION] {planner_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(tuple([planner_message])):
        chunks.append(chunk)
        print(chunk, end="", flush=True)
    planner_response = "".join(chunks)
    log = f"""[RESPONSE] {planner_response}"""
    write_to_file(log_file, log, end_block=True)
    token_count["reasoning"] += count_tokens(planner_response)
    # callback
    onProgress(token_count)
    print('\n----------------------------------------------------------------')
    print('Reasoning about the next best course of action...')
    print('----------------------------------------------------------------\n')

    # get the best tool to use
    reasoning_message = _reasoning_message(plan=planner_response, context=context)
    log = f"""[MODEL_INSTRUCTION] {reasoning_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(tuple([reasoning_message])):
        chunks.append(chunk)

    reasoning_response = "".join(chunks)
    log = f"""[RESPONSE] {reasoning_response}"""
    write_to_file(log_file, log, end_block=True)
    token_count["reasoning"] += count_tokens(reasoning_response)
    # callback
    onProgress(token_count)

    try:
        # parse the reasoning response
        reasoning_response = json.loads(reasoning_response)
    except Exception as error:
        print("\n[ERROR] Error parsing reasoning response")
        print(f"[ERROR] Error: {error}", end="", flush=True)
        print(f"\n[ERROR] Reasoning response: {reasoning_response}", end="", flush=True)
        reasoning_response = {}
        return None

    print('\n----------------------------------------------------------------')
    print('Using the tool...')
    print('----------------------------------------------------------------\n')

    # use the tool
    print(f'\n[INFO] Reasoning response: {reasoning_response}')
    tools = reasoning_response.get("tools", [])
    results = []
    for tool in tools:
        tool_name = next(iter(tool))
        t = tool.get(tool_name, None)
        tool_parameters = t.get('parameters', {})

        # if tool is empty
        if tool_name is None and tool_parameters is None:
            print(f"\n[INFO] No tool to use")
        else:
            try:
                result = run_tool(tool_name, tool_parameters)
                results.append(result)
                print(f"\n[INFO] Result: {result}", end="", flush=True)
            except Exception as error:
                print(f"\n[ERROR] Error running tool: {error}")

        # add the reasoning response to the messages
        log = f"""[TOOL_USED] {tool_name}\n[TOOL_PARAMETERS] {tool_parameters}\n[RESULT] {results}"""
        write_to_file(log_file, log, end_block=True)
    
    print('\n----------------------------------------------------------------')
    print('Completed the task!')
    print('----------------------------------------------------------------')

    return results