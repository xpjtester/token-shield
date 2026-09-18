# Token Shield Plugin

Token Shield Plugin packages three ways to use the same optimizer:

1. **Plugin + MCP** — deterministic context optimization for ChatGPT/Codex. No OpenAI API key is required for the core tools.
2. **Zero-key Web/API** — paste context into the dashboard or call `/api/optimize` directly.
3. **Optional LLM Proxy** — the original OpenAI-compatible `/v1/chat/completions` proxy for developers who already have upstream API access.

## V0.2 architecture

```text
ChatGPT / Codex Plugin
        |
        v
   MCP /mcp  --------------------------+
        |                               |
        v                               |
Deterministic optimizer                 |
- exact paragraph dedupe                |
- blank-line cleanup                    |  no LLM call
- repeated log-run compression          |  no API key
- token measurement                     |
- fenced-code preservation              |
        |                               |
        +--> optimized context <---------+

Optional developer path:
Client -> /v1/chat/completions -> Token Shield -> upstream LLM API
```

The zero-key optimizer does **not** convert a ChatGPT subscription into API credits and does not intercept all ChatGPT traffic. It optimizes only context explicitly sent to Token Shield.

## Run locally — no API key

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. You can paste text into the dashboard immediately.

Useful endpoints:

- `POST /api/optimize` — zero-key context optimizer
- `POST /api/token-stats` — zero-key token measurement
- `/mcp` — Streamable HTTP MCP endpoint
- `/v1/chat/completions` — optional upstream LLM proxy; only this path needs an API key
- `/docs` — FastAPI docs

Example:

```bash
curl -X POST http://localhost:8000/api/optimize \
  -H 'content-type: application/json' \
  -d '{"context":"repeat me\n\nrepeat me\n\nkeep this","mode":"balanced"}'
```

## Plugin package

This repository follows the portable Agent Plugins layout:

```text
plugin.json
mcp.json
.mcp.json                 # Codex compatibility fallback
skills/
  token-shield/
    SKILL.md
.codex-plugin/
  plugin.json
```

`mcp.json` points to `http://localhost:8000/mcp` for local development. For a public ChatGPT/Codex plugin, deploy Token Shield to a stable HTTPS host, replace that URL with `https://YOUR_DOMAIN/mcp`, and set `MCP_ALLOWED_HOSTS` (plus browser origins if needed) before submission.

The MCP server exposes four read-only optimization tools:

- `optimize_context`
- `create_context_capsule`
- `compress_logs`
- `token_stats`

The core MCP tools do not call OpenAI or any other model provider.
They also do not persist the supplied context in V0.2; the dashboard stores only aggregate token metrics for `/api/optimize`.

See `docs/PLUGIN_SETUP.md` for ChatGPT/Codex development and deployment steps.

## Run the MCP server separately

The normal FastAPI app already serves MCP at `/mcp`. For MCP-only deployments you can run:

```bash
token-shield-mcp
```

That defaults to port `8001` and can be changed with `MCP_PORT`.

## Optional OpenAI-compatible proxy

Only configure this if you want the original proxy feature:

```bash
cp .env.example .env
# set OPENAI_API_KEY in .env
uvicorn app.main:app --reload
```

Then:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="your-openai-key")
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Summarize this..."}],
    temperature=0,
)
```

Optional proxy controls:

```json
{"token_shield":{"dedupe":true,"keep_recent":8,"route_model":true,"cache":true}}
```

## Safety rules of the deterministic optimizer

- Fenced code blocks are preserved exactly.
- `safe` mode removes only exact duplicate paragraphs and redundant blank lines.
- `balanced` mode additionally compresses consecutive logs whose payload is identical apart from timestamps.
- Log compression keeps the first and last line of each collapsed run.
- No semantic rewriting or model-generated summary is used in V0.2.

## Docker

No API key is needed unless you use proxy mode:

```bash
docker compose up --build
```

## Test

```bash
pytest
```

## Current production TODOs

- Deploy the MCP endpoint on stable HTTPS, update `mcp.json`/`.mcp.json`, and configure the MCP host allowlist.
- Add rate limiting and abuse protection to the public MCP service.
- Validate the plugin package with the OpenAI plugin submission tooling.
- Add authentication only if future features store user-specific state.
- Add semantic compaction later as an opt-in server feature; keep the default deterministic path zero-key.

## License

MIT
