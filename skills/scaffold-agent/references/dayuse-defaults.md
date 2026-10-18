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

- **Model**: `DAYUSE_MODEL=openrouter/anthropic/claude-sonnet-5.5` via LiteLLM — Claude Sonnet 5.5, released 2026-09-28. We keep Claude, without coupling the code. The plugin teaches Sonnet; each agent switches model with `DAYUSE_MODEL`, no code change. `dayuse-agent-fleet` defaults to GLM (`openrouter/z-ai/glm-5.2`) and pins Sonnet per leaf where it needs it: the divergence is deliberate.
- **Route: OpenRouter, zero data retention forced.** For an `openrouter/*` model, the templates send `provider.zdr: true` on every request: OpenRouter then routes only to ZDR endpoints. `DAYUSE_OPENROUTER_PROVIDER_PREFS` (JSON object, same name as in the fleet) adds routing keys; it cannot switch ZDR off. A direct provider route (`anthropic/…`, `bedrock/…`) gets no `provider` object — it would reject or ignore it — so its ZDR is a contract matter: check it before switching. Belt and braces: also enable ZDR account-wide on OpenRouter; the request flag is OR-ed with the account and guardrail settings. Key: `OPENROUTER_API_KEY`, from the broker/secret manager.
- **EU residency is not guaranteed by this default.** OpenRouter's ZDR endpoints for Sonnet 5.5 are Google Vertex (`google-vertex/global`, `google-vertex/us`, `google-vertex/europe`) and Amazon Bedrock; the first-party Anthropic endpoint is not among them, so `zdr: true` routes away from it (read on 2026-10-14 from `https://openrouter.ai/api/v1/endpoints/zdr`, which OpenRouter keeps current). To keep the model endpoint in the EU: `DAYUSE_OPENROUTER_PROVIDER_PREFS={"order": ["google-vertex/europe"], "allow_fallbacks": false}`, about 10 % dearer. That pins the provider, not OpenRouter's own hop: processing entirely in-region needs in-region routing (`OPENROUTER_API_BASE=https://eu.openrouter.ai/api/v1`; fails closed; enforceable with a guardrail `allowed_data_regions: ["europe"]`) on a Business or Enterprise plan. Dayuse's OpenRouter plan: **to collect**. Personal data: `gdpr-guardrails`.
- **LiteLLM cost map**: `LITELLM_LOCAL_MODEL_COST_MAP=True`. By default LiteLLM fetches its model cost map from GitHub; `True` uses the map bundled with the installed package. Without network, litellm 1.105.1 retried that download at import (Spike A, 2026-10-14; not compared with 1.90.x). The bundled map is the installed version's: Sonnet 5.5 is in 1.105.1's map, not in 1.90.2's (checked in the fleet's venvs). What LiteLLM does for a model missing from the map (call, cost lookup): **to collect**.
- **Identity**: `DAYUSE_IDENTITY_PROVIDER=oidc-mtls`.
- **Port**: `PORT=8080`, the container listens on it (Cloud Run + k8s/Knative compatibility).
- **A2A**: Agent Card served at `/.well-known/agent-card.json`.

## MCP wiring rules

- Wire **only** the MCP servers the agent needs (least privilege).
- The business MCP servers (MySQL, Elasticsearch, RabbitMQ, Sentry, etc.) are configured **in the agent**, never in the `dayuse-agentic-platform` plugin.
- Prefer the **Streamable HTTP** transport for remote servers (HTTPS); `Stdio` for a packaged local server.
- Access tokens via the broker/Vault and the environment, never hard-coded.

Sources: https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html (launch date) · https://openrouter.ai/anthropic/claude-sonnet-5.5 (slug, providers, EU endpoint) · https://openrouter.ai/docs/guides/routing/provider-selection.md (`zdr`, regional slugs) · https://openrouter.ai/docs/guides/features/zdr.md · https://openrouter.ai/docs/guides/features/in-region-routing.md · https://docs.litellm.ai/docs/proxy/custom_model_cost_map

## Never generate

- An import of a cloud model SDK (everything goes through LiteLLM).
- An import of or dependency on `gcp-agent-identity` outside the `get_identity_provider()` factory.
- A write (MR/issue/Notion) without a HITL point.
- A long-lived secret in the image or a committed `.env` (`.env.example` only).
