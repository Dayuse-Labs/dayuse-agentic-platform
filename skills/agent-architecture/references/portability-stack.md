# Dayuse portability stack (detail)

Goal: an agent that runs **anywhere** (Cloud Run, k8s/Knative, dev machine, another cloud) without rewriting. Each layer has a clean boundary and a "zero lock-in" golden rule.

## Layer 1 — Model (LiteLLM)

- **Rule**: the code never references a proprietary model SDK. Always `from google.adk.models.lite_llm import LiteLlm` and `Agent(model=LiteLlm(model=...))`.
- The model (and therefore the provider) is driven by an env variable, e.g. `DAYUSE_MODEL=anthropic/claude-sonnet-4-6`. We keep Claude, but without coupling the code.
- Provider keys come from the environment (`ANTHROPIC_API_KEY`, etc.), never hard-coded.
- **Anti-pattern**: importing a specific cloud client (`vertexai`, Bedrock SDK…) directly into the agent. If a provider requires an SDK, isolate it behind LiteLLM.

## Layer 2 — Execution (OCI container)

- **Rule**: every agent ships as an OCI image. No dependency on a proprietary managed runtime.
- Supported and tested targets:
  - **Cloud Run**: it is just a container runtime; non-blocking, serves as a test target. The container must listen on `$PORT`.
  - **Kubernetes / Knative**: self-hostable prod target. Same image, different manifest.
- The container assumes no cloud metadata server to function (see layer 4 for identity).
- Details and manifests: `deploy-anywhere` skill.
- **Anti-pattern**: reading `http://metadata.google.internal` in the critical path, or assuming a cloud-specific filesystem/secret-manager.

## Layer 3 — Coordination (A2A + MCP)

- **A2A** (agent↔agent): an orchestrator calls leaf agents via `RemoteA2aAgent` pointing at their Agent Card `/.well-known/agent-card.json`. Each leaf exposes itself via `to_a2a()` or `adk api_server --a2a`. See `wire-a2a`.
- **MCP** (agent↔tool): an agent accesses GitLab, Notion, logs, MySQL, Elasticsearch, RabbitMQ, Sentry… via `MCPToolset`. These MCP servers are **wired into the generated agent**, not into this plugin.
- Agent Cards declare the supported auth schemes (`securitySchemes`, OpenAPI 3 style) and can be signed (JWS / JCS). See `agent-identity`.
- **Anti-pattern**: making two agents communicate through a proprietary bus instead of A2A, or embedding a business tool hard-coded into the orchestrator instead of going through MCP.

## Layer 4 — Identity & secrets

- **Rule**: never a raw credential on the agent side. The agent obtains short-lived identities/tokens via a **token broker / Vault** (the portable equivalent of the "Auth Manager").
- The agent identity goes through the **`AgentIdentityProvider`** interface:
  - `oidc-mtls` (portable default): mTLS + signed A2A Agent Cards + OAuth2/OIDC via the Dayuse IdP.
  - `spire` (self-hosted prod target): SPIFFE/SPIRE.
  - `gcp-agent-identity` (optional, GCP only) — **no generated agent should depend on it**.
- Full detail and code skeleton: `agent-identity` skill.
- **Anti-pattern**: mounting a long-lived service-account key into the image, or coupling auth to a non-pluggable cloud identity service.

## "Zero lock-in" checklist (to run before any merge)

1. No import of a proprietary model SDK (everything goes through LiteLLM).
2. No import of / dependency on `gcp-agent-identity`; identity goes through `AgentIdentityProvider`.
3. The container starts without a cloud metadata server and listens on `$PORT`.
4. Secrets come from the environment or the broker/Vault, never from the code or the image.
5. Manifests exist for Cloud Run **and** k8s/Knative from the **same** image.
