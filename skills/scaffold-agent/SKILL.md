---
name: scaffold-agent
description: >
  Scaffolds a single ADK Python leaf agent with the Dayuse defaults. This skill triggers
  when a tech wants to "create an agent", "scaffold an ADK agent", or "generate a specialized
  agent" (coder, tester, MR writer, spec generator/evaluator, etc.). Delegates the generic
  ADK skeleton to the google-agents-cli-scaffold skill and adds only the Dayuse overlay:
  LiteLLM, portable container, pluggable identity, MCP tools, and HITL on writes.
  Do not use for a multi-agent orchestrator (see scaffold-orchestrator).
metadata:
  version: "0.1.0"
---

# Scaffold a Dayuse leaf agent

Produce a **portable** ADK Python agent that is ready to expose over A2A. Follow the steps in order. Do not reimplement the generic ADK: delegate it to `agents-cli`.

## Step 0 — Frame (load the mental model)

Load the `agent-architecture` skill first. Confirm that the need is indeed a **leaf agent**:

- If an equivalent leaf already exists → **do not create one**, reuse it via `scaffold-orchestrator`.
- If the logic serves a single orchestrator and has no stable contract → keep it **inline**, no separate agent.
- Otherwise → continue.

## Step 1 — Check `agents-cli`

Check that the Google `agents-cli` skills are installed (they carry the generic ADK scaffolding). If they are missing, **flag it** to the tech and point to the dependencies section of the plugin README, then continue best-effort with the templates below.

## Step 2 — Collect the minimum needed

Ask only for what is missing:

- **Name** of the agent (snake_case, e.g. `mr_writer`).
- **Role / short description** (feeds the Agent Card and the instruction).
- **System instruction** (what the agent does, its scope).
- **Business MCP tools** needed by THIS agent (GitLab, Notion, logs, MySQL, Elasticsearch, RabbitMQ, Sentry, etc.) — they will be wired in the agent, not in the plugin.
- **Does it write** anywhere (MR, issue, Notion)? If so → enable the **HITL** point.
- **Identity provider** (default `oidc-mtls`).

## Step 3 — Delegate the ADK skeleton to `agents-cli`

Let `agents-cli` generate the base ADK structure (agent package, `agent.py`/`root_agent`, project configuration, standard eval/deploy entry points). Do not duplicate that knowledge here.

## Step 4 — Apply the Dayuse defaults (templates)

Read the templates from `${CLAUDE_PLUGIN_ROOT}/skills/scaffold-agent/templates/` and write them into the agent's project, substituting the placeholders (list in `references/dayuse-defaults.md`). Compose:

- **`agent.py`** (`agent.py.tmpl`) — `root_agent = Agent(model=LiteLlm(...), tools=[MCPToolset(...)])`. Model **always** via LiteLLM, driven by `DAYUSE_MODEL`. Wire the `MCPToolset` entries for the listed business tools.
- **`__init__.py`** (`init.py.tmpl`) — exposes the `agent` module for ADK discovery.
- **`identity/`** — copy the `AgentIdentityProvider` skeleton from `${CLAUDE_PLUGIN_ROOT}/skills/agent-identity/references/identity-providers.md` (provider.py + oidc_mtls.py + spire.py; only include `gcp_agent_identity.py` if explicitly requested). The business code depends only on `get_identity_provider()`.
- **`secrets/broker.py`** — copy the `TokenBroker` from `${CLAUDE_PLUGIN_ROOT}/skills/gdpr-guardrails/references/data-residency.md` if the agent accesses tools that require tokens.
- **`serve.py`** (`serve.py.tmpl`) — A2A exposure by default (auto Agent Card at `/.well-known/agent-card.json`).
- **`agent-card.json`** (`agent-card.json.tmpl`) — manual A2A card (for the `adk api_server --a2a` path and declaring the auth schemes). Finalize/sign via `wire-a2a`.
- **`Dockerfile`** (`Dockerfile.tmpl`) — portable image that listens on `$PORT`.
- **`requirements.txt`** (`requirements.txt.tmpl`) and **`.env.example`** (`env.example.tmpl`).

## Step 5 — Wire the guardrails

- **HITL**: if the agent writes, insert the confirmation point **before** every write (see `gdpr-guardrails`). The plugin's `PreToolUse` hook is the belt; the code is the suspenders.
- **Identity**: `oidc-mtls` by default; never import `gcp-agent-identity`.
- **Secrets**: via the broker/Vault and the environment, never hard-coded.

## Step 6 — Check the invariants (zero-lock-in checklist)

Before concluding, go through the checklist in `agent-architecture/references/portability-stack.md`: no proprietary model SDK, no GCP dependency, a container that starts without a cloud metadata server and listens on `$PORT`, secrets outside the image.

## Step 7 — Next steps (suggest)

- `wire-a2a` — finalize the Agent Card (auth schemes, JWS signature).
- `deploy-anywhere` — generate the Cloud Run and k8s/Knative manifests.
- `eval-agent` — create the evaluation harness.
- To commit the scaffold into GitLab (branch/MR): go through **HITL** (otherwise the hook blocks it).

## Resources

- **`references/dayuse-defaults.md`** — list of placeholders, defaults, target tree, and MCP wiring rules.
- **`templates/`** — template files to copy and substitute.
