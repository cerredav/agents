from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-14B-Instruct")

def tokenize_message(message: str) -> int:
    return tokenizer.encode(message)

def detokenize_message(tokens: list[int]) -> str:
    return tokenizer.decode(tokens)

def count_tokens(message: str) -> int:
    return len(tokenize_message(message))