import json

import tiktoken


def _encoding(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_messages(messages: list[dict], model: str) -> int:
    enc = _encoding(model)
    total = 3
    for message in messages:
        total += 4
        total += len(enc.encode(json.dumps(message, ensure_ascii=False, default=str)))
    return total

