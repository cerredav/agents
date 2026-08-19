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

def _intent_message(capabilities: list) -> Message:
    intent_prompt = read_yml(str(INTENT_PROMPT_PATH))["intent_prompt"]
    # build capabilities
    capas = ""
    for c in capabilities:
        capas += f"""
        Capability: {c.get('capability')} \n
        Tools: {c.get('tools')}
        """
    capas+='\n'
    return {
        "role": "system",
        "content": intent_prompt.format(capabilities=capas),
    }

def _agents_message(user_intent: str, user_input: str) -> Message:
    agents_prompt = read_yml(str(AGENTS_PROMPT_PATH))["node_prompt"]
    return {
        "role": "system",
        "content": agents_prompt.format(user_intent=user_intent, user_input=user_input),
    }

def submit_to_graph(user_input: str, onProgress: Callable | None = None):
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
    intent_message = _intent_message(state.capabilies)
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

    # define number of agents
    planner_message = _agents_message(user_intent=intent_response, user_input=user_input)
    log = f"""[MODEL_INSTRUCTION] {planner_message["content"]}\n"""
    write_to_file(log_file, log)
    chunks = []
    for chunk in stream_model_response(tuple([planner_message])):
        chunks.append(chunk)
        print(chunk, end="", flush=True)

    planner_response = ''.join(chunk)
    print('planner response', planner_response)
    try:
        agents = json.loads(planner_response)
        print('agents', agents)
    except Exception as e:
        print('error parsing json planner_response', planner_response)