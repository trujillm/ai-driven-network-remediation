"""
OpenShift API MCP Server
=========================
MCP server exposing OpenShift operations as tools
for the AI-driven network remediation agent.

Tools:
    get_pods               - List pods in a namespace with status
    get_events             - Get recent OpenShift events (warnings)
    rollout_restart        - Trigger a rolling restart
    patch_deployment_memory - Patch deployment memory limits
    get_pod_logs           - Get recent logs from a specific pod

Transport: Configurable via MCP_TRANSPORT env var (default: sse)
"""

import os
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

MCP_TRANSPORT: Literal["stdio", "sse", "streamable-http"] = os.environ.get(
    "MCP_TRANSPORT", "sse"
)  # type: ignore[assignment]
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")

mcp = FastMCP(
    "noc-openshift",
    instructions=(
        "OpenShift cluster management tools for the NOC remediation agent. "
        "Use these tools to inspect pod status, get logs, patch deployments, "
        "and trigger restarts on the edge cluster."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=(MCP_TRANSPORT == "streamable-http"),
)

EDGE_KUBECONFIG = os.getenv("EDGE_KUBECONFIG", "/kubeconfig/edge-kubeconfig")
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "dark-noc-edge")


@mcp.custom_route("/health", methods=["GET"])  # type: ignore
async def health(request: Any) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "OK"})


def main() -> None:
    """Run the OpenShift MCP server."""
    mcp.run(transport=MCP_TRANSPORT)


app = mcp.streamable_http_app()

from . import tools as _tools  # noqa: E402, F401
