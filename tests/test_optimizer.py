from app.optimizer import optimize


def test_deduplicates_and_trims():
    messages = [{"role": "system", "content": "Be useful"}]
    messages += [{"role": "user", "content": f"message {i}"} for i in range(10)]
    messages += [{"role": "user", "content": "message 9"}]
    result = optimize(messages, "gpt-4.1-mini", None, {"keep_recent": 4, "route_model": False})
    assert len(result.messages) == 5
    assert "deduplicated_messages" in result.actions
    assert "trimmed_history" in result.actions
    assert result.after_tokens < result.before_tokens


def test_simple_task_routes_to_cheap_model():
    result = optimize([{"role": "user", "content": "Translate hello to Dutch"}], None, None, {})
    assert result.model.endswith("nano")
    assert result.max_tokens == 300

