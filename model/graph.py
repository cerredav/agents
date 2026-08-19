import json
from pathlib import Path
from collections.abc import Callable
from utils.read_yml import read_yml

from utils.tokenizer import count_tokens
from .connection import stream_model_response
from utils.write_to_file import write_to_file
from .state import State

Message = dict[str, str]
TokenCount = dict[str, int]

transcript_file = open("transcript_loop.txt", "w")
log_file = open("log_loop.txt", "w")
token_count: TokenCount = {
    "input": 0,
    "output": 0,
    "reasoning": 0
}

INTENT_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "intent.yml"
AGENTS_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "node.yml"
CAPABILITIES_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "capability.yml"

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
        "content": intent_prompt.format(),
    }

def _capabilities_message(user_intent: str, user_input: str, capabilities: str) -> Message:
    agents_prompt = read_yml(str(CAPABILITIES_PROMPT_PATH))["capability_prompt"]
    return {
        "role": "system",
        "content": agents_prompt.format(
            user_intent=user_intent, 
            user_input=user_input,
            capabilities=_get_capabilities(capabilities)
            ),
    }

async def submit_to_graph(user_input: str, onProgress: Callable | None = None):
    """
    Accept a user input and start the graph
    """
    context = ''

    state = State(user_input = user_input)
    state.define_capabilities()

    user_message = {
        "role": "user", 
        "content": user_input
    }
    # decipher a user's intent
    intent_message = _intent_message()
    intent_message_array = [
        intent_message,
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

    # get capability pack
    capability_message = _capabilities_message(
        user_intent=intent_response, 
        user_input=user_input,
        capabilities=state.capabilies
    )
    log = f"""[MODEL_INSTRUCTION] {capability_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(tuple([capability_message])):
        chunks.append(chunk)

    capability_response = ''.join(chunks)
    capabilities = None
    try:
        capabilities = json.loads(capability_response)
    except Exception as e:
        print('error parsing json planner_response', capability_response)


    from .react import submit_to_agent
    import asyncio

    print('-----------------capabilties-----------------', capabilities)
    agents = [
        submit_to_agent(
            user_input=user_input,
            user_intent=intent_response,
            onProgress=onProgress,
            capability=capability
        ) for capability in capabilities
    ]
    result = await asyncio.gather(*agents)

    for r in result:
        if r is not None:
            context += r
    return context
