import re
from dataclasses import dataclass

from app.config import settings
from app.tokenizer import count_messages


@dataclass
class OptimizationResult:
    messages: list[dict]
    model: str
    max_tokens: int
    before_tokens: int
    after_tokens: int
    actions: list[str]


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return str(content)


def _dedupe(messages: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    output: list[dict] = []
    for message in messages:
        key = (message.get("role", ""), _text(message.get("content", "")).strip())
        if key in seen and key[0] != "system":
            continue
        seen.add(key)
        output.append(message)
    return output


def _trim_history(messages: list[dict], keep: int) -> list[dict]:
    pinned = [m for m in messages if m.get("role") in {"system", "developer"}]
    conversational = [m for m in messages if m.get("role") not in {"system", "developer"}]
    return pinned + conversational[-keep:]


def _task_complexity(messages: list[dict]) -> str:
    last = next((_text(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"), "")
    complex_signals = r"\b(debug|architect|analy[sz]e|proof|strategy|refactor)\b|代码|架构|分析|证明|策略"
    simple_signals = r"^(translate|summarize|classify|extract|rewrite|翻译|总结|分类|提取)\b"
    if re.search(complex_signals, last, re.I) or len(last) > 1800:
        return "complex"
    if re.search(simple_signals, last.strip(), re.I) or len(last) < 180:
        return "simple"
    return "normal"


def optimize(messages: list[dict], requested_model: str | None, requested_max: int | None, options: dict) -> OptimizationResult:
    original_model = requested_model or settings.default_model
    before = count_messages(messages, original_model)
    actions: list[str] = []

    optimized = _dedupe(messages) if options.get("dedupe", True) else messages
    if len(optimized) != len(messages):
        actions.append("deduplicated_messages")

    keep = int(options.get("keep_recent", settings.max_recent_messages))
    trimmed = _trim_history(optimized, keep)
    if len(trimmed) != len(optimized):
        actions.append("trimmed_history")
    optimized = trimmed

    complexity = _task_complexity(optimized)
    if options.get("route_model", True):
        model = settings.cheap_model if complexity == "simple" else (settings.fallback_model if complexity == "complex" else original_model)
        if model != original_model:
            actions.append(f"routed_model:{model}")
    else:
        model = original_model

    budget = {"simple": 300, "normal": 700, "complex": settings.max_output_tokens}[complexity]
    max_tokens = min(requested_max or budget, settings.max_output_tokens)
    if requested_max is None or max_tokens < requested_max:
        actions.append(f"output_budget:{max_tokens}")

    after = count_messages(optimized, model)
    return OptimizationResult(optimized, model, max_tokens, before, after, actions)

