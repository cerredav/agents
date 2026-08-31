import json
from pathlib import Path
from collections.abc import Callable
from typing import Any
from utils.context.date import get_current_datetime_context
from utils.context.injection import collect_context, inject_rules
from utils.read_yml import read_response_format, read_yml

from utils.tokenizer import count_tokens
from .connection import stream_model_response
from utils.print_agent_thought import (
    make_agent_thought_callback,
    print_agent_thought,
)
from utils.write_to_file import write_to_file
from .state import State

Message = dict[str, str]
TokenCount = dict[str, int]

transcript_file = open("transcript_loop.txt", "w")
# Append mode prevents the later import of react.py from erasing graph logs.
log_file = open("log_loop.txt", "a")
token_count: TokenCount = {
    "input": 0,
    "output": 0,
    "reasoning": 0
}

PROMPTS_PATH = Path(__file__).parents[1] / "prompts"
INTENT_PROMPT_PATH = PROMPTS_PATH / "intent" / "prompt.yml"
AGENTS_PROMPT_PATH = PROMPTS_PATH / "node" / "prompt.yml"
CAPABILITIES_PROMPT_PATH = PROMPTS_PATH / "capability" / "prompt.yml"

INTENT_RESPONSE_FORMAT = read_response_format(INTENT_PROMPT_PATH)
CAPABILITIES_RESPONSE_FORMAT = read_response_format(CAPABILITIES_PROMPT_PATH)

def _thinking_callback(title: str) -> Callable[[str], None]:
    """Print a model thought and persist the same trace in the loop log."""
    return make_agent_thought_callback(
        title=title,
        on_thought=lambda thought: write_to_file(
            log_file,
            f"[MODEL_THOUGHT] {title}\n{thought}",
            end_block=True,
        ),
    )

def _get_capabilities(capabilities: list, *, tools: bool = False) -> str:
    # get capabilities in str
    capas = ""
    for c in capabilities:
        capas += f"""
        Capability: {c.get('capability')} \n
        """
        if tools:
            capas += f"{c.get('tools')}"
    capas+='\n'
    return capas

def _intent_message() -> Message:
    intent_prompt = read_yml(str(INTENT_PROMPT_PATH))["intent_prompt"]
    return {
        "role": "system",
        "content": inject_rules(intent_prompt.format()),
    }

def _capabilities_message(user_intent: str, user_input: str, capabilities: str) -> Message:
    agents_prompt = read_yml(str(CAPABILITIES_PROMPT_PATH))["capability_prompt"]
    return {
        "role": "system",
        "content": inject_rules(
            agents_prompt.format(
                user_intent=user_intent,
                user_input=user_input,
                capabilities=_get_capabilities(capabilities),
            )
        ),
    }

async def submit_to_graph(
    user_input: str,
    onProgress: Callable | None = None,
    *,
    runtime_context: dict[str, Any] | None = None,
):
    """
    Accept a user input and start the graph
    """
    context = ''
    runtime_context = runtime_context or collect_context(get_current_datetime_context)
    log_file.seek(0)
    log_file.truncate()

    state = State(user_input = user_input)

    # Intent deciphering is temporarily disabled.
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

    # get capability pack
    capability_message = _capabilities_message(
        user_intent=intent_response,
        user_input=user_input,
        capabilities=state.capabilies
    )
    log = f"""[MODEL_INSTRUCTION] {capability_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(
        tuple([capability_message]),
        response_format=CAPABILITIES_RESPONSE_FORMAT,
        on_thinking=_thinking_callback("Capability reasoning"),
    ):
        chunks.append(chunk)

    capability_response = ''.join(chunks)
    print_agent_thought(capability_response, title="Selected capabilities")
    capabilities = None
    try:
        capabilities = json.loads(capability_response)
    except Exception as e:
        print('error parsing json planner_response', capability_response)


    from .react import submit_to_agent
    import asyncio

    print_agent_thought(f"\nCreating {len(capabilities)} ReAct loops", title="React Loops")
    agents = [
        submit_to_agent(
            user_input=user_input,
            user_intent=intent_response,
            onProgress=onProgress,
            capability=capability,
            runtime_context=runtime_context,
        ) for capability in capabilities
    ]
    result = await asyncio.gather(*agents)

    for r in result:
        if r is not None:
            context += r
    return context
