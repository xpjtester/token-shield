import re
from dataclasses import asdict, dataclass
from typing import Literal

from app.tokenizer import count_text

Mode = Literal["safe", "balanced"]

_FENCE_RE = re.compile(r"(```.*?```)", re.DOTALL)
_TIMESTAMP_PREFIX = re.compile(
    r"^\s*(?:\[)?(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)(?:\])?\s*"
)


@dataclass(slots=True)
class TextOptimizationResult:
    optimized_text: str
    before_tokens: int
    after_tokens: int
    saved_tokens: int
    reduction_percent: float
    actions: list[str]
    mode: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_exact(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _dedupe_paragraphs(text: str) -> tuple[str, int]:
    paragraphs = re.split(r"\n\s*\n", text)
    seen: set[str] = set()
    output: list[str] = []
    removed = 0

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        key = _normalize_exact(stripped)
        if len(key) >= 12 and key in seen:
            removed += 1
            continue
        seen.add(key)
        output.append(stripped)

    return "\n\n".join(output), removed


def _collapse_blank_lines(text: str) -> tuple[str, bool]:
    collapsed = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    return collapsed, collapsed != text


def _log_signature(line: str) -> str:
    return _TIMESTAMP_PREFIX.sub("", line).strip()


def _compress_log_runs(text: str, min_run: int = 4) -> tuple[str, int]:
    """Collapse consecutive timestamp-only log repetition while preserving endpoints."""
    lines = text.splitlines()
    if not lines:
        return text, 0

    output: list[str] = []
    collapsed_count = 0
    i = 0
    while i < len(lines):
        signature = _log_signature(lines[i])
        if not signature:
            output.append(lines[i])
            i += 1
            continue

        j = i + 1
        while j < len(lines) and _log_signature(lines[j]) == signature:
            j += 1

        run = j - i
        if run >= min_run:
            output.append(lines[i])
            hidden = run - 2
            output.append(f"[Token Shield collapsed {hidden} repeated log lines]")
            output.append(lines[j - 1])
            collapsed_count += hidden
        else:
            output.extend(lines[i:j])
        i = j

    return "\n".join(output), collapsed_count


def _optimize_non_code(segment: str, mode: Mode) -> tuple[str, list[str]]:
    actions: list[str] = []
    current, removed = _dedupe_paragraphs(segment)
    if removed:
        actions.append(f"deduplicated_paragraphs:{removed}")

    current, changed = _collapse_blank_lines(current)
    if changed:
        actions.append("collapsed_blank_lines")

    if mode == "balanced":
        current, collapsed = _compress_log_runs(current)
        if collapsed:
            actions.append(f"compressed_repeated_logs:{collapsed}")

    return current, actions


def optimize_context(text: str, mode: Mode = "balanced", model: str = "gpt-4.1-mini") -> TextOptimizationResult:
    """Deterministically compact context without calling an LLM.

    Fenced code blocks are preserved byte-for-byte. Outside fenced code, Token Shield
    only removes exact duplicate paragraphs, redundant blank lines and (in balanced
    mode) consecutive log lines whose payload is identical apart from timestamps.
    """
    if mode not in {"safe", "balanced"}:
        raise ValueError("mode must be 'safe' or 'balanced'")

    before = count_text(text, model)
    actions: list[str] = []
    pieces = _FENCE_RE.split(text)
    optimized_pieces: list[str] = []

    for piece in pieces:
        if piece.startswith("```") and piece.endswith("```"):
            optimized_pieces.append(piece)
            continue
        optimized, piece_actions = _optimize_non_code(piece, mode)
        optimized_pieces.append(optimized)
        actions.extend(piece_actions)

    optimized_text = "".join(optimized_pieces).strip()
    after = count_text(optimized_text, model)
    saved = max(0, before - after)
    reduction = round((saved / before) * 100, 1) if before else 0.0

    if not actions:
        actions.append("no_safe_reduction_found")

    actions = list(dict.fromkeys(actions))
    return TextOptimizationResult(
        optimized_text=optimized_text,
        before_tokens=before,
        after_tokens=after,
        saved_tokens=saved,
        reduction_percent=reduction,
        actions=actions,
        mode=mode,
    )


def deduplicate_context(text: str, model: str = "gpt-4.1-mini") -> TextOptimizationResult:
    return optimize_context(text, mode="safe", model=model)


def compress_logs(text: str, model: str = "gpt-4.1-mini") -> TextOptimizationResult:
    before = count_text(text, model)
    optimized, collapsed = _compress_log_runs(text, min_run=3)
    optimized, blank_changed = _collapse_blank_lines(optimized)
    after = count_text(optimized, model)
    saved = max(0, before - after)
    actions: list[str] = []
    if collapsed:
        actions.append(f"compressed_repeated_logs:{collapsed}")
    if blank_changed:
        actions.append("collapsed_blank_lines")
    if not actions:
        actions.append("no_repeated_log_runs_found")
    return TextOptimizationResult(
        optimized_text=optimized,
        before_tokens=before,
        after_tokens=after,
        saved_tokens=saved,
        reduction_percent=round((saved / before) * 100, 1) if before else 0.0,
        actions=actions,
        mode="logs",
    )


def token_stats(text: str, optimized_text: str | None = None, model: str = "gpt-4.1-mini") -> dict:
    before = count_text(text, model)
    after = count_text(optimized_text, model) if optimized_text is not None else before
    saved = max(0, before - after)
    return {
        "before_tokens": before,
        "after_tokens": after,
        "saved_tokens": saved,
        "reduction_percent": round((saved / before) * 100, 1) if before else 0.0,
        "model": model,
    }
