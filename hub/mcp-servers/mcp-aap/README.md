# MCP AAP

MCP server wrapping the Ansible Automation Platform REST API for the AI-driven network remediation agent.

## Tools

| Tool | Description |
|---|---|
| `list_job_templates` | List available Ansible job templates |
| `launch_job` | Trigger a job template execution by name |
| `upsert_job_template` | Create or update a template for a playbook path |
| `get_job_status` | Poll job completion status |
| `get_job_output` | Get stdout from a completed or failed job |

## Environment Variables

| Variable | Required | Default |
|---|---|---|
| `AAP_USERNAME` | Yes | — |
| `AAP_PASSWORD` | Yes | — |
| `AAP_URL` | No | `https://aap.aap.svc` |
| `AAP_API_PREFIX` | No | `/api/v2` |
| `AAP_VERIFY_SSL` | No | `true` |
| `MCP_TRANSPORT` | No | `sse` |
| `MCP_PORT` | No | `8000` |

## Running Locally

```bash
export AAP_USERNAME=admin AAP_PASSWORD=password
export AAP_URL=http://localhost:8082  # point at an AAP mock or real controller
export AAP_VERIFY_SSL=false
export MCP_TRANSPORT=streamable-http
uv run uvicorn mcp_aap:app --host 0.0.0.0 --port 8000
```

## Tests

```bash
# Unit tests (mocks all HTTP calls)
AAP_USERNAME=test AAP_PASSWORD=test uv sync --group dev && uv run pytest

# Integration tests run via: make integration-tests
```
