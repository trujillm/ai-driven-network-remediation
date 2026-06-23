# NOC Frontend — V1

React dashboard for the AI-Driven Network Remediation quickstart. Polls the chatbot BFF and displays real-time operational status.

## Quick Start

```bash
# Terminal 1: port-forward the BFF
oc port-forward -n hub svc/hub-chatbot-service 8080:80

# Terminal 2: run the dev server
cd hub/frontend
npm install
npm run dev
# Open http://localhost:5173
```

The Vite dev server proxies `/api/*` to `localhost:8080` automatically.

## Tech Stack

- React 19 + Vite 6
- Plain CSS (dark NOC theme)
- nginx (production container)
- No external UI framework

## Architecture

```
┌──────────────┐       /api/*        ┌─────────────────────┐
│   Browser    │ ───────────────────► │  nginx (frontend)   │
│  React SPA   │                      │  proxy to BFF       │
└──────────────┘                      └────────┬────────────┘
                                               │
                                               ▼
                                      ┌─────────────────────┐
                                      │  hub-chatbot-service │
                                      │  (FastAPI BFF)       │
                                      └─────────────────────┘
```

In development, Vite's built-in proxy replaces nginx.

## BFF Endpoints Consumed

| Endpoint | Method | Interval | What it drives |
|----------|--------|----------|----------------|
| `/api/summary` | GET | 10s poll | Header metrics, status cards |
| `/api/integrations` | GET | 10s poll | Integration matrix, SLO, business impact, incident timeline |
| `/api/chat` | POST | User action | Chat panel |
| `/api/demo/trigger` | POST | User action | Demo trigger buttons |

## Project Structure

```
hub/frontend/
├── package.json          # Dependencies (react, vite)
├── vite.config.js        # Dev server + API proxy
├── index.html            # SPA entry
├── Containerfile         # Multi-stage build (node → nginx)
├── nginx.conf            # Reverse proxy for /api/*
└── src/
    ├── main.jsx          # React root
    ├── App.jsx           # Layout orchestrator
    ├── styles.css        # Dark NOC theme
    ├── hooks/
    │   └── usePolling.js # 10s interval polling hook
    └── components/
        ├── DegradedBanner.jsx    # Amber banner for _deps.status: "degraded"
        ├── HeaderMetrics.jsx     # Hero bar with totals
        ├── StatusCards.jsx       # 6 status cards (dep-aware)
        ├── IntegrationMatrix.jsx # MCP/platform health grid
        ├── SloPanel.jsx          # SLO metrics
        ├── BusinessImpact.jsx    # Cost/time savings
        ├── IncidentTimeline.jsx  # Incident movie replay
        ├── DemoTrigger.jsx       # 4 demo scenario buttons
        └── ChatPanel.jsx         # NOC chat with structured replies (dep-aware)
```

## API Response Shapes (V1)

The BFF returns nested objects. Key differences from the POC:

```js
// Chat response
data.model.name        // not data.model_name
data.model.source      // not data.model_source
data.model.framework   // new field
data.context.open_incidents    // not data.open_incidents
data.context.integrations_up   // not data.integrations_up

// Summary
data.servicenow = { mode: "mock", reachable: true }  // not a string

// Demo trigger success
data.incident_id  // UUID for traceability

// Demo trigger failure
HTTP 502 + { status: "error", detail: "..." }  // not HTTP 200
```

### Dependency Status (`_deps`)

All BFF data endpoints now include a `_deps` field signaling whether the response contains complete or partial data:

```jsonc
// All deps healthy — data is complete
{ "_deps": { "status": "ok" }, "open_incidents": 3, ... }

// Some deps unavailable — data is partial/fallback
{ "_deps": { "status": "degraded", "unavailable": ["kafka", "servicenow"] }, "open_incidents": 0, ... }
```

The frontend handles this with a single universal check:

| Condition | UI Behavior |
|-----------|-------------|
| `_deps.status === "ok"` (or `_deps` absent) | Normal display — no visual change |
| `_deps.status === "degraded"` | Amber banner at page top listing unavailable deps; affected cards show "unavailable" instead of misleading zeros |

Per-endpoint degradation mapping:

| Endpoint | Degrades when | Frontend effect |
|----------|---------------|-----------------|
| `/api/summary` | ServiceNow unreachable | ServiceNow card → "unavailable", Open Incidents card → "unavailable" |
| `/api/integrations` | Kafka or any probe down | Amber banner appears |
| `/api/chat` | LLM unreachable (fallback reply) | Reply annotated with `[⚠ Partial — ... unavailable]` |
| `/api/demo/trigger` | Kafka down | HTTP 502 (existing error handling) |

## Build & Deploy

```bash
# Build container image
make build-frontend-image

# Push to registry
podman push quay.io/rh-ai-quickstart/noc-frontend:0.1.0

# Deploy with Helm (deploys all services including frontend)
make helm-install
```

The Helm chart creates a Deployment, Service, and OpenShift Route with TLS edge termination.

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `VITE_CHATBOT_URL` | Dev only | Override BFF target (default: relative `/api/*`) |

In production, nginx handles the proxy — no env vars needed at runtime.

## Tested On

Verified end-to-end on OpenShift cluster `ai-dev04.kni.syseng.devcluster.openshift.com`:

- Image: `quay.io/rh-ee-mtalvi/noc-frontend:0.1.0`
- Route: `https://hub-frontend-hub.apps.ai-dev04.kni.syseng.devcluster.openshift.com`
- BFF proxy: nginx → `hub-chatbot-service.hub.svc.cluster.local:80`

All panels render with live data, polling refreshes every 10s, demo triggers return `incident_id`, and chat returns structured executive replies with model metadata.

## V1 Demo Flow

### What the presenter does

1. Open the dashboard at the frontend Route URL
2. Show the live state — panels polling every 10s, MCP servers up/down, SLO metrics
3. Click a demo trigger button (e.g., "Trigger CrashLoop Demo")
4. Observe the result — `incident_id` appears, confirming event was queued
5. Watch the dashboard update — after ~10-30s, incident timeline / SLO metrics change
6. Use the chat — ask "Executive summary of current incident posture" to get a narrative

### What happens under the hood

```
Step 1: User clicks "Trigger CrashLoop Demo"
           │
           ▼
Step 2: Frontend → POST /api/demo/trigger {scenario: "crashloop", site: "edge-01"}
           │
           ▼
Step 3: BFF generates a UUID incident_id, builds a failure event message
        (e.g., "CrashLoopBackOff: nginx configuration test failed")
           │
           ▼
Step 4: BFF publishes the event to Kafka topic "system-alerts"
        → Returns incident_id + kafka_offset to the frontend
           │
           ▼
Step 5: LangGraph agent-service (ideally) consumes from "system-alerts"
        → Runs the graph: normalize → RAG → analyze → decide → remediate/escalate → notify → audit
           │
           ▼
Step 6: Agent writes result to Kafka topic "incident-audit"
        (includes RCA, decision, remediation result, artifacts)
           │
           ▼
Step 7: On next poll cycle (10s), BFF reads "incident-audit" topic
        → Computes updated SLO metrics (MTTD, MTTR, auto-remediation %)
        → Builds incident movie timeline entry
           │
           ▼
Step 8: Frontend receives updated /api/integrations data
        → Incident Timeline shows the new event with stage badge
        → SLO numbers update
        → Business Impact counters increment
```

### What's working today vs. what's placeholder

| Step | Status | Notes |
|------|--------|-------|
| 1-4 (Trigger → Kafka) | Working | Tested — got `incident_id` back |
| 5 (Agent consumes from Kafka) | Not wired | Agent only has `POST /remediate` HTTP endpoint; no Kafka consumer loop yet |
| 6 (Agent writes audit) | Not wired | Agent `audit` node is a placeholder |
| 7-8 (BFF reads audit → dashboard updates) | Working | BFF reads `incident-audit` topic; if records existed, they'd appear |

### In V1 today, the demo story is

1. You trigger a scenario → proves Kafka connectivity and event publishing
2. You see the `incident_id` → proves traceability
3. You use the chat → proves the LLM/fallback narrative works with live MCP context
4. The dashboard shows live infra health → proves the monitoring surface works

The gap: there is no Kafka consumer loop in `agent-service` to automatically pick up the event and close the loop. The agent only has a REST endpoint (`POST /remediate`). The "incident appears in timeline after 30s" part won't happen automatically until someone wires the agent to consume from `system-alerts`.

### Full E2E demo workaround

You can manually invoke the agent after triggering:

```bash
curl -X POST http://localhost:8007/remediate \
  -H "Content-Type: application/json" \
  -d '{"raw_event": "CrashLoopBackOff: nginx configuration test failed"}'
```

This doesn't write to `incident-audit` either (the audit node is a stub), so the full autonomous loop is a V2 milestone — the frontend is ready for it.

## Open Question: Should the Autonomous Loop Be Part of V1?

The `aap-mock` and `servicenow-mock` are deployed and running. The MCP servers (`mcp-noc-aap`, `mcp-noc-servicenow`, `mcp-noc-slack`) are healthy and pointing to them. However, **nobody invokes them during a demo** because the agent-service has no Kafka consumer loop — it only exposes `POST /remediate`.

Today the mocks serve one purpose: they make the Integration Status Matrix show green "UP" pills. Without them, those MCP servers would fail health probes and the dashboard would look broken.

The missing piece for a complete demo is:

```
system-alerts (Kafka) → agent consumes → LangGraph runs → MCP tools called
    → aap-mock receives restart/playbook request
    → servicenow-mock receives create_incident
    → slack MCP logs notification
    → agent writes to incident-audit (Kafka)
    → BFF picks up audit record on next poll
    → Dashboard updates: incident timeline, SLO, business impact
```

Without this, the demo story is: "we can trigger events, we can chat, we can see infra health" — but we cannot show the **autonomous remediation loop** end-to-end.

**Question for the team:** Should wiring the agent Kafka consumer + closing the audit loop be a V1 requirement, or is the current "trigger + observe + chat" flow sufficient for V1 and the autonomous loop moves to V2?
