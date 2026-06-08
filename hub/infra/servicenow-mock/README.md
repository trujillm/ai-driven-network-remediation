# ServiceNow Mock

Lightweight FastAPI server simulating the ServiceNow REST Table API for CI and local development.

## Running Locally

```bash
uv sync --group dev
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

## Running Tests

```bash
uv sync --group dev
uv run pytest -v
```

Also included in `make unit-tests` from the repo root.

## Deploying to a Cluster

```bash
# Via Makefile (builds, pushes, deploys)
make build-push-servicenow-mock deploy-servicenow-mock

# Or as part of full install
ENABLE_SERVICENOW_MOCK=true make helm-install
```

## API Surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/now/table/incident` | POST | Create incident |
| `/api/now/table/incident/{number}` | GET | Get incident |
| `/api/now/table/incident/{number}` | PATCH | Update incident |
| `/api/now/table/incident` | GET | List incidents |
| `/api/now/table/sys_user` | GET | Lookup user |
| `/api/now/table/sys_user` | POST | Create user |
| `/healthz` | GET | Readiness probe |

Auth: `X-API-Key` header (default key: `demo-api-key-2026`, configurable via `API_KEY` env var).
