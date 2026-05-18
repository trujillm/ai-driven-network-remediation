"""
Kafka MCP Server
=================
MCP server for Kafka operations.
Allows the AI remediation agent to read from topics and produce messages.

Tools:
    consume_topic   - Read recent messages from a topic
    produce_message - Write a message to a topic
    get_consumer_lag - Check consumer group lag
    list_topics     - List all available topics

Transport: Configurable via MCP_TRANSPORT env var (default: sse)
"""

import os
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

MCP_TRANSPORT: Literal["stdio", "sse", "streamable-http"] = os.environ.get(
    "MCP_TRANSPORT", "sse"
)  # type: ignore[assignment]
MCP_PORT = int(os.environ.get("MCP_PORT", "8003"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")

mcp = FastMCP(
    "noc-kafka",
    instructions=(
        "Kafka streaming tools for the NOC remediation agent. "
        "Use consume_topic to read recent messages for analysis. "
        "Use produce_message to send remediation events or audit records. "
        "Use get_consumer_lag to check if the agent is keeping up with log volume."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=(MCP_TRANSPORT == "streamable-http"),
)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "dark-noc-kafka-kafka-bootstrap.dark-noc-kafka.svc:9092")


@mcp.custom_route("/health", methods=["GET"])  # type: ignore
async def health(request: Any) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "OK"})


def main() -> None:
    """Run the Kafka MCP server."""
    mcp.run(transport=MCP_TRANSPORT)


app = mcp.streamable_http_app()

from . import tools as _tools  # noqa: E402, F401
