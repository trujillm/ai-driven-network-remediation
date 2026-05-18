"""
Slack MCP Server
=================
MCP server wrapping the Slack Bot API as tools for the AI remediation agent.
Sends NOC alerts, remediation summaries, and status updates to Slack.

Tools:
    send_alert          - Send a formatted NOC alert with severity color
    send_message        - Send a plain text message
    send_remediation    - Send a remediation summary with status
    send_incident_ticket - Send ServiceNow ticket info to Slack

Transport: Configurable via MCP_TRANSPORT env var (default: sse)
"""

import os
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

MCP_TRANSPORT: Literal["stdio", "sse", "streamable-http"] = os.environ.get(
    "MCP_TRANSPORT", "sse"
)  # type: ignore[assignment]
MCP_PORT = int(os.environ.get("MCP_PORT", "8005"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")

mcp = FastMCP(
    "noc-slack",
    instructions=(
        "Slack notification tools for the NOC remediation agent. "
        "Always use send_alert for incidents with severity. "
        "Use send_remediation after a fix is applied. "
        "Keep messages concise — engineers read them on mobile."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=(MCP_TRANSPORT == "streamable-http"),
)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_NOC_CHANNEL = os.getenv("SLACK_NOC_CHANNEL", "#dark-noc-alerts")
SLACK_BASE_URL = "https://slack.com/api"


@mcp.custom_route("/health", methods=["GET"])  # type: ignore
async def health(request: Any) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "OK"})


def main() -> None:
    """Run the Slack MCP server."""
    mcp.run(transport=MCP_TRANSPORT)


app = mcp.streamable_http_app()

from . import tools as _tools  # noqa: E402, F401
