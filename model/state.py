from dataclasses import dataclass
from typing import List, Callable, Any

@dataclass
class Tool:
    name: str
    description: str

# state of the graph
@dataclass
class State:
    user_input: str = None
    intent: str = None
    current_tools: List[Tool] = None
    last_tools: List[Tool] = None
    runtime_context: dict[str, Any] = None

    # use singleton pattern
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # Create the object if it does not exist yet
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_intent(cls, intent):
        cls.intent = intent

    def add_node(cls,):
        cls.nodes += 1

    def define_capabilities(cls):
        from capabilities import get_all
        cls.capabilies = get_all()