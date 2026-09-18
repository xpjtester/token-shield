---
name: token-shield
description: Reduce repetitive or oversized context, logs, and pasted history before using it in a task. Use when the user asks to save tokens, shrink context, compress logs, remove duplicated history, create a compact context capsule, or diagnose context bloat.
---

Use the `token-shield` MCP tools. Core optimization is deterministic and does not require an OpenAI API key.

1. For general pasted context, call `optimize_context` with `mode="balanced"` unless the user explicitly asks for the safest/minimal transformation; then use `mode="safe"`.
2. For logs dominated by repeated lines, call `compress_logs`.
3. For measurement only, call `token_stats`.
4. When the user asks for a reusable compact handoff, call `create_context_capsule`.
5. Report the before/after token counts, saved tokens, reduction percentage, and the optimizer actions.
6. Treat fenced code returned by Token Shield as exact preserved content. Do not silently rewrite it after the tool returns it.
7. Never claim that Token Shield intercepts all ChatGPT traffic or converts a ChatGPT subscription into API credits. It optimizes only the context explicitly sent to its tools.
8. If no safe reduction is found, say so instead of inventing a summary.
