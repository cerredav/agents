
# state of the graph
class State:
    nodes: int
    intent: str

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