import os
from typing import Literal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.context_optimizer import compress_logs as compress_log_text
from app.context_optimizer import optimize_context as optimize_context_text
from app.context_optimizer import token_stats as calculate_token_stats

SERVER_INSTRUCTIONS = (
    "Token Shield reduces context bloat deterministically and does not call an LLM. "
    "Use optimize_context for general text, compress_logs for repetitive logs, and "
    "token_stats when only measurement is needed. Preserve the returned optimized text exactly."
)

mcp = MCPServer(name="token-shield", version="0.2.0", instructions=SERVER_INSTRUCTIONS)


def transport_security_settings() -> TransportSecuritySettings | None:
    """Use the SDK localhost defaults unless deployment allowlists are configured."""
    hosts = [x.strip() for x in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if x.strip()]
    origins = [x.strip() for x in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",") if x.strip()]
    if not hosts and not origins:
        return None
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


@mcp.tool()
def optimize_context(context: str, mode: Literal["safe", "balanced"] = "balanced") -> dict:
    """Reduce redundant context without an API key or model call.

    Fenced code is preserved exactly. Safe mode removes only exact duplicate paragraphs
    and extra blank lines. Balanced mode also collapses repeated timestamped log runs.
    """
    if not context.strip():
        raise ValueError("context must not be empty")
    return optimize_context_text(context, mode=mode).to_dict()


@mcp.tool()
def create_context_capsule(context: str) -> dict:
    """Create a compact context payload plus token savings metadata."""
    if not context.strip():
        raise ValueError("context must not be empty")
    result = optimize_context_text(context, mode="balanced")
    data = result.to_dict()
    data["capsule"] = result.optimized_text
    return data


@mcp.tool()
def compress_logs(log_text: str) -> dict:
    """Collapse consecutive repetitive log lines while preserving the first and last line."""
    if not log_text.strip():
        raise ValueError("log_text must not be empty")
    return compress_log_text(log_text).to_dict()


@mcp.tool()
def token_stats(text: str, optimized_text: str | None = None) -> dict:
    """Measure tokens locally; no API key and no model request are used."""
    return calculate_token_stats(text, optimized_text)


def run() -> None:
    port = int(os.getenv("MCP_PORT", "8001"))
    host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        transport_security=transport_security_settings(),
    )


if __name__ == "__main__":
    run()
