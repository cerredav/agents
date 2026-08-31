from pathlib import Path
from collections.abc import Callable
from typing import Any
from typing_extensions import runtime

from utils.context.date import get_current_datetime_context
from utils.context.injection import collect_context, inject_rules
from .connection import stream_model_response
from utils.tokenizer import count_tokens
from utils.write_to_file import write_to_file
from utils.print_agent_thought import (
    make_agent_thought_callback,
    print_agent_thought,
)
from utils.read_yml import read_response_format, read_yml
from utils.parse_tools import format_tools_for_prompt
from utils.run_tool import run_tool
from .state import State

import json

Message = dict[str, str]
TokenCount = dict[str, int]

state = State()

transcript_file = open("transcript_loop.txt", "w")
# Graph and capability loops share this append-only handle without truncating
# one another's diagnostic history.
log_file = open("log_loop.txt", "a")
token_count: TokenCount = {
    "input": 0,
    "output": 0,
    "reasoning": 0
}

PROMPTS_PATH = Path(__file__).parents[1] / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_PATH / "system" / "prompt.yml"
INTENT_PROMPT_PATH = PROMPTS_PATH / "intent" / "prompt.yml"
REASONING_PROMPT_PATH = PROMPTS_PATH / "reasoning" / "prompt.yml"
LOOP_PROMPT_PATH = PROMPTS_PATH / "loop" / "prompt.yml"
PLANNER_PROMPT_PATH = PROMPTS_PATH / "planner" / "prompt.yml"
OBSERVE_PROMPT_PATH = PROMPTS_PATH / "observe" / "prompt.yml"
REACT_PROMPT_PATH = PROMPTS_PATH / "react" / "prompt.yml"

INTENT_RESPONSE_FORMAT = read_response_format(INTENT_PROMPT_PATH)
PLANNER_RESPONSE_FORMAT = read_response_format(PLANNER_PROMPT_PATH)
OBSERVE_RESPONSE_FORMAT = read_response_format(OBSERVE_PROMPT_PATH)

def _thinking_callback(title: str, *, capability: str | None = None) -> Callable[[str], None]:
    """Print a model thought and persist the same trace in the loop log."""
    stage = f"{title} [{capability}]" if capability else title
    return make_agent_thought_callback(
        title=stage,
        on_thought=lambda thought: write_to_file(
            log_file,
            f"[MODEL_THOUGHT] {stage}\n{thought}",
            end_block=True,
        ),
    )

def _intent_message() -> Message:
    intent_prompt = read_yml(str(INTENT_PROMPT_PATH))["intent_prompt"]
    return {
        "role": "system",
        "content": inject_rules(intent_prompt),
    }

def _planner_message(
    user_input: str,
    user_intent: str,
    context: str,
    *,
    capability: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> Message:
    planner_prompt = read_yml(str(PLANNER_PROMPT_PATH))["planner_prompt"]
    planner_str = planner_prompt.format(
        user_input=user_input,
        user_intent=user_intent, 
        context=context
    )

    if capability:
        planner_str = f"You are a planning {capability} agent. " + planner_str
    planner_str = inject_rules(planner_str, runtime_context)
    return {
        "role": "system",
        "content": planner_str,
    }

def _reasoning_message(
    user_input: str,
    # plan: str,
    context: str,
    *,
    capability: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> Message:
    reasoning_prompt = read_yml(str(REASONING_PROMPT_PATH))["reasoning_prompt"]
    system_tools = format_tools_for_prompt(capability=capability)
    content = reasoning_prompt.format(
        user_input=user_input,
        # plan=plan,
        system_tools=system_tools,
        context=context,
    )
    return {
        "role": "system",
        "content": inject_rules(content, runtime_context),
    }

def _observe_message(
    context: str,
    user_request: str,
    *,
    runtime_context: dict[str, Any] | None = None,
) -> Message:
    observe_prompt = read_yml(str(OBSERVE_PROMPT_PATH))["observe_prompt"]
    content = observe_prompt.format(context=context, user_request=user_request)
    return {
        "role": "system",
        "content": inject_rules(content, runtime_context),
    }

def _parse_observation(response: str) -> tuple[bool, str]:
    """Parse the structured completion observation returned by the model."""
    try:
        observation = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(f"Observation is not valid JSON: {error}") from error

    if not isinstance(observation, dict):
        raise ValueError("Observation must be a JSON object.")
    complete = observation.get("complete")
    reason = observation.get("reason")
    if not isinstance(complete, bool) or not isinstance(reason, str):
        raise ValueError("Observation requires a boolean 'complete' and string 'reason'.")
    return complete, reason

async def submit_to_loop(user_input: str, onProgress: Callable | None = None):
    """
    Accept a user input and start the loop
    """
    log_file.seek(0)
    log_file.truncate()
    has_completed = False
    context = ''
    runtime_context = collect_context(get_current_datetime_context)

    state.user_input = user_input
    state.runtime_context=runtime_context

    user_message = {
        "role": "user",
        "content": user_input,
    }
    intent_message = _intent_message()
    intent_message_array = [
        intent_message,
        user_message,
    ]
    log = (
        f'[USER_INPUT] {user_input}\n'
        f'[MODEL_INSTRUCTION] {intent_message["content"]}\n'
    )
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(
        tuple(intent_message_array),
        response_format=INTENT_RESPONSE_FORMAT,
        on_thinking=_thinking_callback("Intent reasoning"),
    ):
        chunks.append(chunk)
    intent_response = "".join(chunks)
    state.intent = intent_response
    print_agent_thought(intent_response, title="Interpreted intent")
    log = f"[RESPONSE]{intent_response}"
    write_to_file(log_file, log, end_block=True)
    intent_response_tokens = count_tokens(intent_response)
    token_count["reasoning"] += intent_response_tokens
    onProgress(token_count)

    # Use the original request until intent deciphering is re-enabled.
    intent_response = user_input
    log = (
        f"[USER_INPUT] {user_input}\n"
        f"[INTENT_BYPASS] Using raw user input as intent: {intent_response}"
    )
    write_to_file(log_file, log, end_block=True)


    # start loop until the model finishes.
    # finishing rule is to have has_completed=True
    while not has_completed:
        # think and act
        result = think(
            user_input=user_input,
            users_intent=intent_response,
            context=context,
            onProgress=onProgress,
            runtime_context=runtime_context,
        )
        context += f"[TOOL_RESULT] {result}\n"
        observe_message = _observe_message(
            context=context,
            user_request=user_input,
            runtime_context=runtime_context,
        )

        print('----------------------------------------------------------------')
        print('Observing the tool result...')
        print('----------------------------------------------------------------\n')

        loop_response = ""
        loop_chunks = []
        print()
        log = f"""[MODEL_INSTRUCTION] {observe_message["content"]}\n"""
        write_to_file(log_file, log)
        # observe
        for chunk in stream_model_response(
            tuple([observe_message]),
            response_format=OBSERVE_RESPONSE_FORMAT,
            on_thinking=_thinking_callback("Observation reasoning"),
        ):
            loop_chunks.append(chunk)

        loop_response = "".join(loop_chunks)
        log = f"""[RESPONSE] {loop_response}"""
        write_to_file(log_file, log, end_block=True)

        # parse the loop response
        print_agent_thought(loop_response, title="Completion observation")
        loop_response_tokens = count_tokens(loop_response)
        token_count["reasoning"] += loop_response_tokens
        # callback
        onProgress(token_count)
        try:
            has_completed, reason = _parse_observation(loop_response.strip())
            print(f'[INFO] Has completed: {has_completed}. Reason: {reason}')
        except Exception as error:
            print(f'\n[ERROR] Error parsing loop response: {error}')
            print(f'\n[ERROR] Loop response: {loop_response}')
            loop_response = False
            has_completed = False

    return context

async def submit_to_agent(
    user_input: str,
    user_intent: str,
    onProgress: Callable | None = None,
    *,
    capability: str | None = None,
    runtime_context: dict[str, Any] | None = None,
):
    has_completed = False
    context = ''
    runtime_context = runtime_context or collect_context(get_current_datetime_context)

    # start loop until the model finishes.
    # finishing rule is to have has_completed=True
    while not has_completed:
        # think and act
        result = think(
            user_input,
            user_intent,
            context=context,
            onProgress=onProgress,
            capability=capability,
            runtime_context=runtime_context,
        )
        context += f"[TOOL_RESULT] {result}\n"
        observe_message = _observe_message(
            context=context,
            user_request=user_input,
            runtime_context=runtime_context,
        )

        loop_response = ""
        loop_chunks = []
        log = f"""[MODEL_INSTRUCTION] {observe_message["content"]}\n"""
        write_to_file(log_file, log)
        # observe
        for chunk in stream_model_response(
            tuple([observe_message]),
            response_format=OBSERVE_RESPONSE_FORMAT,
            on_thinking=_thinking_callback(
                "Observation reasoning",
                capability=capability,
            ),
        ):
            loop_chunks.append(chunk)

        loop_response = "".join(loop_chunks)
        log = f"""[RESPONSE] {loop_response}"""
        write_to_file(log_file, log, end_block=True)

        # parse the loop response
        print_agent_thought(loop_response, title="Completion observation")
        loop_response_tokens = count_tokens(loop_response)
        token_count["reasoning"] += loop_response_tokens
        # callback
        onProgress(token_count)
        try:
            has_completed, reason = _parse_observation(loop_response.strip())
            print(f'[INFO] Has completed: {has_completed}. Reason: {reason}')
        except Exception as error:
            print(f'\n[ERROR] Error parsing loop response: {error}')
            print(f'\n[ERROR] Loop response: {loop_response}')
            loop_response = False
            has_completed = False

    return context

def think(
    user_input: str,
    users_intent: str,
    context: str,
    onProgress: Callable,
    *,
    capability: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> tuple[str, str, str, str]:
    # plan the next best course of action
    # planner_message = _planner_message(
    #     user_input=user_input,
    #     user_intent=users_intent,
    #     context=context,
    #     capability=capability,
    #     runtime_context=runtime_context,
    # )
    # log = f"""[MODEL_INSTRUCTION] {planner_message["content"]}\n"""
    # write_to_file(log_file, log)
    # chunks = []
    # for chunk in stream_model_response(
    #     tuple([planner_message]),
    #     response_format=PLANNER_RESPONSE_FORMAT,
    #     on_thinking=_thinking_callback(
    #         "Planning reasoning",
    #         capability=capability,
    #     ),
    # ):
    #     chunks.append(chunk)

    # planner_response = "".join(chunks)
    # print_agent_thought(planner_response, title="Planner response")
    # log = f"""[RESPONSE] {planner_response}"""
    # write_to_file(log_file, log, end_block=True)
    # token_count["reasoning"] += count_tokens(planner_response)
    # # callback
    # onProgress(token_count)

    # get the best tool to use
    reasoning_message = _reasoning_message(
        user_input=user_input,
        # plan=planner_response, 
        context=context, 
        capability=capability,
        runtime_context=runtime_context,
    )
    log = f"""[MODEL_INSTRUCTION] {reasoning_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(
        tuple([reasoning_message]),
        on_thinking=_thinking_callback(
            "Tool-choice reasoning",
            capability=capability,
        ),
    ):
        chunks.append(chunk)

    reasoning_response = "".join(chunks)
    print_agent_thought(reasoning_response, title="Tool selection")
    log = f"""[RESPONSE] {reasoning_response}"""
    write_to_file(log_file, log, end_block=True)
    token_count["reasoning"] += count_tokens(reasoning_response)
    # callback
    onProgress(token_count)

    try:
        # parse the reasoning response
        reasoning_response = json.loads(reasoning_response)
    except Exception as error:
        print_agent_thought(
            f"Response: {reasoning_response}\nError: {error}",
            title="Reasoning Response",
            style="red",
        )
        reasoning_response = {}
        return None

    # use the tool
    tools = reasoning_response.get("tools", [])
    # update tool list
    if state.last_tools:
        state.last_tools = state.current_tools
        state.current_tools = tools

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
                print_agent_thought(result, title="Tool result")
                results.append(result)
            except Exception as error:
                print_agent_thought(
                    f"Tool name: {tool_name}\n"
                    f"Tool Parameters: {tool_parameters}\n"
                    f"Error: {error}",
                    title="Tool Result",
                    style="red",
                )

        # add the reasoning response to the messages
        log = f"""[TOOL_USED] {tool_name}\n[TOOL_PARAMETERS] {tool_parameters}\n[RESULT] {results}"""
        write_to_file(log_file, log, end_block=True)
    
    return results
