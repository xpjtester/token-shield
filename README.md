# Token Shield

OpenAI-compatible proxy that reduces repeated input context and excessive output budgets before requests reach an LLM.

## What works in this MVP

- Message deduplication and bounded recent history
- Simple/normal/complex model routing
- Automatic output-token budgets
- Exact deterministic-response cache
- Streaming passthrough
- SQLite usage metrics and live dashboard
- Per-response optimization audit in `token_shield`

The optimizer is deliberately conservative: it does not rewrite code, numbers, constraints, or system prompts.

## Run locally

```bash
cp .env.example .env
# add OPENAI_API_KEY to .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. API docs are at <http://localhost:8000/docs>.

## Use as an OpenAI drop-in

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="your-openai-key")
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Summarize this..."}],
    temperature=0,
)
print(response.choices[0].message.content)
```

Optional proxy controls can be sent as an extra top-level object:

```json
{"token_shield":{"dedupe":true,"keep_recent":8,"route_model":true,"cache":true}}
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Important current limitations

- Cache is exact-match, not semantic yet.
- Streaming requests record input savings, but completion-token accounting is deferred.
- Pricing/cost estimates are not included until model prices are configured explicitly.
- Production deployment should add authentication, rate limits, encrypted secrets, Postgres/Redis, and tenant isolation.

## Test

```bash
pytest
```

## License

MIT

