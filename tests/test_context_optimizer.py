from app.context_optimizer import compress_logs, optimize_context, token_stats


def test_safe_mode_removes_exact_duplicate_paragraphs():
    text = "Keep this requirement exactly.\n\nSome explanatory paragraph.\n\nSome explanatory paragraph."
    result = optimize_context(text, mode="safe")
    assert result.optimized_text.count("Some explanatory paragraph.") == 1
    assert result.after_tokens < result.before_tokens
    assert any(action.startswith("deduplicated_paragraphs") for action in result.actions)


def test_fenced_code_is_preserved_exactly():
    code = "```python\nx = 1\nx = 1\n```"
    text = f"Intro\n\nIntro\n\n{code}\n\nTail"
    result = optimize_context(text, mode="balanced")
    assert code in result.optimized_text


def test_balanced_mode_compresses_repeated_timestamped_logs():
    text = "\n".join(
        [
            "2026-09-18T09:00:00Z worker healthy",
            "2026-09-18T09:00:01Z worker healthy",
            "2026-09-18T09:00:02Z worker healthy",
            "2026-09-18T09:00:03Z worker healthy",
            "2026-09-18T09:00:04Z worker healthy",
        ]
    )
    result = optimize_context(text, mode="balanced")
    assert "Token Shield collapsed" in result.optimized_text
    assert result.after_tokens < result.before_tokens


def test_log_tool_preserves_first_and_last_line():
    lines = [f"2026-09-18T09:00:0{i}Z ping ok" for i in range(5)]
    result = compress_logs("\n".join(lines))
    assert lines[0] in result.optimized_text
    assert lines[-1] in result.optimized_text


def test_token_stats_accepts_preoptimized_text():
    stats = token_stats("alpha beta gamma alpha beta gamma", "alpha beta gamma")
    assert stats["after_tokens"] <= stats["before_tokens"]
    assert stats["saved_tokens"] >= 0
