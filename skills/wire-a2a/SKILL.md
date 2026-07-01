---
name: wire-a2a
description: >
  Exposes an existing ADK agent over A2A with the Dayuse conventions. This skill triggers
  when a developer wants to "expose an agent over A2A", "publish the Agent Card", "serve
  /.well-known/agent-card.json", or "declare the auth schemes" of an agent. Builds and
  serves the Agent Card on /.well-known/agent-card.json, declares the securitySchemes
  consistent with the identity provider, and signs it (JWS/JCS) via the agent-identity
  skill's signing primitive. Suitable for the retrofit of an already-scaffolded agent.
metadata:
  version: "0.1.0"
---

# Expose an agent over A2A

Make an existing ADK agent callable by orchestrators, in an authenticated way. Load `agent-architecture` and `agent-identity` first.

## Step 1 — Identify the target

Locate the agent's package and its `root_agent`. Check that it follows the Dayuse overlay (LiteLLM, `identity/`). If not, complete it with `scaffold-agent`.

## Step 2 — Choose the exposure mode

Two paths (delegate the ADK detail to `agents-cli`):

1. **`to_a2a()` (auto card)** — the simplest. `serve.py` wraps `root_agent`; the Agent Card is generated and published on `/.well-known/agent-card.json`. Serve via uvicorn. Suitable when the default card is enough.
2. **`adk api_server --a2a` (manual card)** — provide an explicit `agent-card.json` (see `references/agent-card-spec.md`). Suitable when you need fine-grained control over skills, auth schemes, or signing.

## Step 3 — Complete the Agent Card

Fill in the required fields (`name`, `description`, `version`, `url`, `capabilities`, `defaultInputModes/OutputModes`, `skills`). Schema details: `references/agent-card-spec.md`. The `url` comes from an env variable (`AGENT_PUBLIC_URL`), never hard-coded.

## Step 4 — Declare the auth schemes

Declare `securitySchemes` (OpenAPI 3 style) consistent with the active identity provider:

- `oidc-mtls` → an `openIdConnect` scheme (Dayuse issuer) **and** `mutualTLS`.
- `spire` → require X.509-SVID mTLS (and/or JWT-SVID as bearer).

Declare in `security` which schemes are required. The A2A server applies `identity.verify_inbound()` on each inbound call.

## Step 5 — Sign the card

Sign the Agent Card with `identity.sign_agent_card(card)`: JWS (RFC 7515) over the JCS-canonicalized card (RFC 8785). Publish the signed card. Orchestrators verify via `identity.verify_agent_card()` before calling.

## Step 6 — Verify interoperability

- The card is reachable on `/.well-known/agent-card.json` and valid.
- A `RemoteA2aAgent` pointing at the URL resolves, verifies the signature, and calls the agent.
- The declared auth schemes are actually required (an unauthenticated call is rejected).

## Step 7 — Register & guardrails

- If the leaf is new, **register it**: append an entry (`name`, `description`, `card_url`, `env`, `owner`, `writes`) to `agents-registry.yaml` at the platform repo root — schema and seed template in `scaffold-orchestrator/references/reuse-registry.md` (create the file from `${CLAUDE_PLUGIN_ROOT}/skills/scaffold-orchestrator/templates/agents-registry.yaml.tmpl` if it does not exist yet). The commit goes through **HITL** (GitLab write).
- If the leaf writes (MR/issue/Notion), mark `writes: true`; HITL applies at the caller.
- Every GitLab commit goes through HITL.

## Resources

- **`references/agent-card-spec.md`** — full A2A Agent Card schema, `securitySchemes` examples, and the JWS/JCS signing procedure.
