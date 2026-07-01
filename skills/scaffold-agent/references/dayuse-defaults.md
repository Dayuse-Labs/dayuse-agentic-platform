# Dayuse defaults & placeholders (scaffold-agent)

## Target tree of a leaf agent

```
<agent_name>/
├── <agent_name>/
│   ├── __init__.py              # from . import agent
│   ├── agent.py                 # root_agent = Agent(model=LiteLlm(...), tools=[MCPToolset(...)])
│   ├── identity/                # copied from the agent-identity skill
│   │   ├── provider.py
│   │   ├── oidc_mtls.py
│   │   └── spire.py             # (+ gcp_agent_identity.py ONLY if requested)
│   └── secrets/
│       └── broker.py            # copied from gdpr-guardrails (if tool access)
├── serve.py                     # A2A exposure (to_a2a)
├── agent-card.json              # manual A2A card (finalized by wire-a2a)
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md                    # includes the GDPR section (data: nature/transit/residency)
```

The generic ADK skeleton (structure, project conventions) is produced by `agents-cli`; the files above are the Dayuse overlay.

## Placeholders to substitute

| Placeholder | Meaning | Example |
|---|---|---|
| `{{AGENT_NAME}}` | snake_case name | `mr_writer` |
| `{{AGENT_DESCRIPTION}}` | short description | `Writes and pushes a GitLab Merge Request` |
| `{{AGENT_INSTRUCTION}}` | system instruction | `You write clear MRs from a diff…` |
| `{{PRIMARY_MCP_ENV}}` | env var for the URL of the primary business MCP | `GITLAB_MCP_URL` |

For multiple MCP servers, duplicate the `MCPToolset` block in `agent.py` (one per business tool), each driven by its own env variable.

## Defaults

- **Model**: `DAYUSE_MODEL=anthropic/claude-sonnet-4-6` via LiteLLM. We keep Claude, without coupling the code.
- **Identity**: `DAYUSE_IDENTITY_PROVIDER=oidc-mtls`.
- **Port**: `PORT=8080`, the container listens on it (Cloud Run + k8s/Knative compatibility).
- **A2A**: Agent Card served at `/.well-known/agent-card.json`.

## MCP wiring rules

- Wire **only** the MCP servers the agent needs (least privilege).
- The business MCP servers (MySQL, Elasticsearch, RabbitMQ, Sentry, etc.) are configured **in the agent**, never in the `dayuse-agentic-platform` plugin.
- Prefer the **Streamable HTTP** transport for remote servers (HTTPS); `Stdio` for a packaged local server.
- Access tokens via the broker/Vault and the environment, never hard-coded.

## Never generate

- An import of a cloud model SDK (everything goes through LiteLLM).
- An import of or dependency on `gcp-agent-identity` outside the `get_identity_provider()` factory.
- A write (MR/issue/Notion) without a HITL point.
- A long-lived secret in the image or a committed `.env` (`.env.example` only).
