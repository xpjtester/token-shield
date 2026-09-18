# Token Shield Plugin setup

## Goal

Use Token Shield from ChatGPT/Codex without asking the user for an OpenAI API key.
The MCP service performs deterministic context optimization only; it does not call an LLM.

## Local development

Start Token Shield:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

MCP endpoint:

```text
http://localhost:8000/mcp
```

Codex/local MCP clients can connect to that endpoint directly.

## ChatGPT developer testing

ChatGPT needs an MCP endpoint it can reach. For development, expose the local server through a secure MCP tunnel or deploy it temporarily to HTTPS, then register that endpoint in ChatGPT developer mode.

The plugin package already contains:

- `plugin.json` — portable Agent Plugins manifest
- `mcp.json` — portable Streamable HTTP MCP config
- `.codex-plugin/plugin.json` + `.mcp.json` — compatibility fallback
- `skills/token-shield/SKILL.md` — workflow instructions

## Public deployment

Before public submission:

1. Deploy the FastAPI app on a stable HTTPS domain.
2. Replace the localhost MCP URL in both `mcp.json` and `.mcp.json`.
3. Set `MCP_ALLOWED_HOSTS` to the exact production host values. Include both the bare hostname and `hostname:*` if the deployment can present an explicit port.
4. Set `MCP_ALLOWED_ORIGINS` only when browser clients need an Origin allowlist.
5. Add rate limiting/abuse protection in front of the public service.
6. Publish a privacy policy explaining that V0.2 does not persist the context submitted to MCP optimization tools.
7. Validate all four tools with MCP Inspector and ChatGPT developer mode before submission.

Example production environment:

```env
MCP_ALLOWED_HOSTS=token-shield.example.com,token-shield.example.com:*
MCP_ALLOWED_ORIGINS=https://chatgpt.com
```

Use the actual production origin(s); do not copy the example blindly.

## What users need

For the core plugin: no OpenAI API key.

For the optional `/v1/chat/completions` developer proxy: an upstream API key is still required because that route actually calls an LLM provider.
