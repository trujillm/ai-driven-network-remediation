"""
LokiStack MCP Server
======================
MCP server for querying LokiStack via the LogQL API.
Gives the AI remediation agent access to historical log data.

Tools:
    query_logs        - Run a LogQL query against LokiStack
    get_recent_errors - Get recent error logs from a namespace/app
    count_errors      - Count error occurrences in a time window

Transport: Configurable via MCP_TRANSPORT env var (default: sse)
"""

import os
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

MCP_TRANSPORT: Literal["stdio", "sse", "streamable-http"] = os.environ.get(
    "MCP_TRANSPORT", "sse"
)  # type: ignore[assignment]
MCP_PORT = int(os.environ.get("MCP_PORT", "8002"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")

mcp = FastMCP(
    "noc-lokistack",
    instructions=(
        "LokiStack log query tools using LogQL. "
        "Use get_recent_errors for quick error lookups. "
        "Use query_logs for complex LogQL queries. "
        "Time range: use relative durations like '1h', '30m', '7d'."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=(MCP_TRANSPORT == "streamable-http"),
)

LOKI_URL = os.getenv("LOKI_URL", "http://logging-loki-gateway.openshift-logging.svc:8080")
LOKI_TOKEN = os.getenv("LOKI_TOKEN", "")
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "dark-noc-edge")


@mcp.custom_route("/health", methods=["GET"])  # type: ignore
async def health(request: Any) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "OK"})


def main() -> None:
    """Run the LokiStack MCP server."""
    mcp.run(transport=MCP_TRANSPORT)


app = mcp.streamable_http_app()

from . import tools as _tools  # noqa: E402, F401
