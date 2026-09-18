import json
import re

try:
    import tiktoken
except ImportError:  # pragma: no cover - deterministic fallback for lightweight/plugin runtimes
    tiktoken = None


def _encoding(model: str):
    if tiktoken is None:
        return None
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_text(text: str, model: str = "gpt-4.1-mini") -> int:
    """Count tokens without requiring an API call.

    Uses tiktoken when available. The regex fallback keeps Token Shield usable in
    lightweight plugin/sandbox runtimes where optional native dependencies are absent.
    """
    enc = _encoding(model)
    if enc is not None:
        return len(enc.encode(text))
    if not text:
        return 0
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def count_messages(messages: list[dict], model: str) -> int:
    total = 3
    for message in messages:
        total += 4
        total += count_text(json.dumps(message, ensure_ascii=False, default=str), model)
    return total
