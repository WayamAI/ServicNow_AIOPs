# ServiceNow AIOPs Agent Server

Automated Docker container incident detection, diagnosis, and remediation using LangGraph multi-agent orchestration.

## Overview

When a Docker container fails, the system automatically:

1. **Detects** the failure via background monitoring
2. **Diagnoses** the root cause (RCA agent)
3. **Plans** a remediation strategy (Plan agent)
4. **Executes** the fix (Execution agent)
5. **Validates** the resolution (Validation agent)
6. **Retries** up to N times if validation fails

All agent activity is streamed in real-time via Server-Sent Events (SSE).

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM — RCA + Execution | Azure OpenAI (Codestral) |
| LLM — Plan + Validation | Azure OpenAI (GPT-4o-mini) |
| Database | SQLite (WAL mode) |
| Streaming | Server-Sent Events (SSE) |
| Package manager | UV |
| Logging | structlog (JSON) |

## Project Structure

```
servicenow-aiops/
├── main.py                    # FastAPI app entry point
├── src/
│   ├── config.py              # Settings (pydantic-settings, AIOPS_ env prefix)
│   ├── db.py                  # SQLite persistence — all CRUD helpers
│   ├── models.py              # Pydantic request/response models
│   ├── errors.py              # Domain exception hierarchy
│   ├── logger.py              # structlog JSON logging
│   ├── bus.py                 # Thread-safe in-process EventBus for SSE
│   ├── callbacks.py           # Event payload utilities
│   ├── ws_callback.py         # LangChain → EventBus callback handler
│   ├── orchestrator.py        # LangGraph StateGraph pipeline
│   ├── state.py               # Retry state wrapper
│   ├── run_registry.py        # Active run registry for cancellation
│   ├── monitor.py             # Docker container monitor (background task)
│   ├── reporter.py            # Markdown + JSON incident report generator
│   ├── agents/
│   │   ├── base.py            # BaseAgent (AzureChatOpenAI + tool calling)
│   │   ├── rca.py             # Root Cause Analysis (Codestral)
│   │   ├── plan.py            # Remediation planner (GPT-4o-mini)
│   │   ├── execution.py       # Fix executor (Codestral)
│   │   └── validation.py      # Resolution validator (GPT-4o-mini)
│   ├── tools/
│   │   ├── docker_tools.py    # docker ps/logs/inspect/start/restart/stop/stats
│   │   ├── git_tools.py       # git pull/add/commit/checkout/push + gh pr create
│   │   ├── read_tool.py       # Read workspace files (path-confined)
│   │   ├── write_tool.py      # Write config files (extension allowlist)
│   │   ├── update_tool.py     # Update dependency files
│   │   └── command_tool.py    # Shell commands (allowlist/denylist)
│   ├── prompts/
│   │   └── agent_prompts.py   # System + human prompt templates
│   └── routes/
│       ├── sessions.py        # Session CRUD
│       ├── incidents.py       # Incident management + pipeline trigger
│       ├── stream.py          # SSE event stream
│       ├── control.py         # Run cancellation + runtime config
│       └── monitor.py         # Monitor container management
└── tests/
```

## Setup

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/)
- Docker CLI in PATH
- Azure OpenAI resource with Codestral and GPT-4o-mini deployments

### Install

```bash
uv sync
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
AIOPS_AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AIOPS_AZURE_OPENAI_API_KEY=your-api-key
AIOPS_CODESTRAL_DEPLOYMENT=codestral
AIOPS_GPT4O_MINI_DEPLOYMENT=gpt-4o-mini
```

### Run

```bash
uv run uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

## Pipeline

```
START → RCA → PLAN → EXECUTE → VALIDATE
                                   │
                          ┌────────┴────────┐
                     validated?         not validated
                          │                  │
                       RESOLVED         retry < max?
                                       yes │    │ no
                                        RCA     FAILED
```

## API Reference

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions` | Create session |
| GET | `/sessions` | List sessions |
| GET | `/sessions/{id}` | Get session |
| PATCH | `/sessions/{id}` | Update config |
| DELETE | `/sessions/{id}` | Cancel session |

### Incidents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/{id}/incidents` | Create incident (triggers pipeline) |
| GET | `/sessions/{id}/incidents` | List incidents |
| GET | `/incidents/{id}` | Get incident with run history |
| GET | `/incidents/{id}/report` | Get markdown + JSON report |

### Stream

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions/{id}/stream` | SSE stream of real-time agent events |

### Control

| Method | Path | Description |
|--------|------|-------------|
| POST | `/runs/{id}/cancel` | Cancel an active run |
| GET | `/config` | Get server config |
| PATCH | `/config` | Update runtime config |

### Monitor

| Method | Path | Description |
|--------|------|-------------|
| POST | `/monitor/containers` | Add container to watch list |
| DELETE | `/monitor/containers/{name}` | Remove container |
| GET | `/monitor/containers` | List monitored containers |
| GET | `/monitor/status` | Monitor health |

## Usage Example

### Manual incident

```bash
# Create a session
SESSION=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.id')

# Watch the SSE stream (in another terminal)
curl -N http://localhost:8000/sessions/$SESSION/stream

# Create an incident
curl -X POST http://localhost:8000/sessions/$SESSION/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "nginx container exited",
    "description": "The nginx container stopped unexpectedly",
    "container_name": "my-nginx"
  }'
```

### Automatic monitoring

```bash
# Add a container to monitor
curl -X POST http://localhost:8000/monitor/containers \
  -H "Content-Type: application/json" \
  -d '{"container_name": "my-nginx", "image": "nginx:latest"}'

# Stop the container — incident is auto-created and remediated
docker stop my-nginx
```

## Configuration

All settings use the `AIOPS_` environment variable prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AIOPS_AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AIOPS_AZURE_OPENAI_API_KEY` | — | Azure OpenAI API key |
| `AIOPS_AZURE_OPENAI_API_VERSION` | `2024-10-21` | API version |
| `AIOPS_CODESTRAL_DEPLOYMENT` | `codestral` | Codestral deployment name |
| `AIOPS_GPT4O_MINI_DEPLOYMENT` | `gpt-4o-mini` | GPT-4o-mini deployment name |
| `AIOPS_DB_PATH` | `aiops.db` | SQLite database path |
| `AIOPS_MONITOR_POLL_INTERVAL` | `15` | Container poll interval (seconds) |
| `AIOPS_MAX_INCIDENT_RETRIES` | `3` | Max pipeline retry attempts |
| `AIOPS_MAX_TOOL_ITERATIONS` | `10` | Max agent tool calls per step |
| `AIOPS_HOST` | `0.0.0.0` | Server bind address |
| `AIOPS_PORT` | `8000` | Server port |

## Development

```bash
# Lint
uv run ruff check .

# Format
uv run black .

# Tests
uv run pytest
```
