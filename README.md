# dayuse-agentic-platform

Internal Dayuse plugin that turns any engineer's Claude Code (or Cowork) into an expert for **building our modular agentic architecture**: portable ADK Python agents, orchestrators that reuse A2A leaf agents, pluggable identity with zero cloud lock-in, and GDPR / human-in-the-loop guardrails.

> This plugin is for **building** agents. It is **not** the agent runtime. Business/infrastructure MCP servers (MySQL, Elasticsearch, RabbitMQ, Sentry…) are wired into the generated agents, not embedded here.

## Dependency: Google `agents-cli` skills

The plugin sits **on top of** the 7 `agents-cli` skills. It does not reimplement the generic ADK knowledge (scaffolding, patterns, eval, standard deployment): it **delegates** that to `agents-cli` and encodes only Dayuse's added value (conventions, portability, identity, guardrails).

Install the `google-agents-cli-*` skills **before** using the scaffolding. If they are missing, the Dayuse skills flag it and run in best-effort mode, but the optimal experience assumes they are present.

## Installation from the GitLab marketplace

The plugin is published on our private GitLab marketplace `claude-plugins-marketplace`.

In a Claude Code session:

```
/plugin marketplace add https://gitlab.com/dayuse/claude-plugins-marketplace.git
/plugin install dayuse-agentic-platform@claude-plugins-marketplace
```

(Adapt the URL to Dayuse's actual GitLab host if self-managed.) In Cowork, install the plugin from the organization's plugin gallery.

## Configuration (environment variables)

The plugin bundles **two documentation MCPs**: `context7` (generic ADK/A2A/MCP/LiteLLM docs) and `adk-docs` (the **official** ADK docs, `adk.dev`).

> **Prerequisite**: `adk-docs` is a **stdio** server launched via `uvx`, so **`uv` must be installed** on the machine ([uv docs](https://docs.astral.sh/uv/)). Without `uv`, this server will not start — the skills keep working (context7 takes over), but you lose the authoritative ADK docs.

| Variable | What for | Example |
|---|---|---|
| `CONTEXT7_API_KEY` | Authenticated use of Context7 (docs quota) | `c7_...` |

`adk-docs` requires no environment variable (it fetches `adk.dev/llms.txt`).

**GitLab is not embedded.** The skills (scaffolding in repos, publishing MRs, searching for existing agents) use the **GitLab MCP you have already connected** in your environment — your implementation, never an imposed official MCP. The plugin declares no GitLab server and no GitLab URL: this avoids duplicate connections and lock-in. The HITL hook recognizes write operations by the **tool name**, whatever GitLab MCP is used.

Credentials (tokens) **always** via the environment, never hard-coded. Remote servers are over HTTPS.

The agents **generated** by this plugin use their own variables (documented in their `.env.example`): `DAYUSE_MODEL`, `ANTHROPIC_API_KEY`, `DAYUSE_IDENTITY_PROVIDER`, `DAYUSE_OIDC_ISSUER`, `DAYUSE_TOKEN_BROKER_URL`, `PORT`, `AGENT_PUBLIC_URL`, and the URLs of their business MCPs.

## Components

### Skills — knowledge (auto-loaded based on context)

| Skill | Role |
|---|---|
| `agent-architecture` | Mental model: orchestrator vs A2A leaf agent, when to share/reuse, 4-layer portability stack, "pluggable identity" reminder. |
| `agent-identity` | `AgentIdentityProvider` interface + 3 implementations: `oidc-mtls` (default), `spire`, `gcp-agent-identity` (optional). |
| `gdpr-guardrails` | Data residency (EU), token broker / Vault, mandatory HITL on write operations. |

### Skills — action (context-triggered)

These skills activate automatically when you describe the matching need — there is no command to type. Describe what you want to do, and the skill loads.

| Skill | Triggers when you want to… |
|---|---|
| `scaffold-agent` | Scaffold a portable ADK Python leaf agent (LiteLLM, container, identity, MCP, A2A Agent Card). |
| `scaffold-orchestrator` | Scaffold an orchestrator + its A2A leaves, **reusing** existing agents. |
| `wire-a2a` | Expose an agent over A2A: Agent Card served at `/.well-known/agent-card.json`, auth schemes, signature. |
| `deploy-anywhere` | Containerize and deploy (Cloud Run + k8s/Knative) from the same image. |
| `eval-agent` | Set up an ADK evaluation harness + cases verifying the Dayuse invariants (HITL, LiteLLM, zero GCP dependency). |

### Hook

`PreToolUse` (prompt) — forces a **human confirmation** before any write operation (push an MR, GitLab issue, Notion write). This is the HITL safety belt.

### Subagents

- `agent-design-reviewer` — reviews an agent/orchestrator design **before** scaffolding (granularity, sharing/reuse, portability, identity, GDPR/HITL).
- `portability-compliance-auditor` — audits the **generated** agent/orchestrator **after** scaffolding: runs the static guardrail and reasons over the zero-lock-in checklist, GDPR, and HITL on writes.

### MCP (bundled)

- **`context7`** — generic docs (ADK, A2A, MCP, LiteLLM…), HTTP transport, optional key.
- **`adk-docs`** — the **official** ADK docs (`adk.dev/llms.txt`), stdio via `uvx`/`mcpdoc`. Authoritative source for pure ADK. **Requires `uv`** (see Configuration).

GitLab is **not** embedded: the skills rely on the GitLab MCP already connected in your environment (see Configuration).

## Architecture decisions (non-negotiable)

1. **Framework**: ADK Python. Go is reserved for MCP servers and performance-critical tools.
2. **Coordination**: A2A (orchestrator → leaves), MCP (agent → tools).
3. **Deployable anywhere**: container by default, model provider via LiteLLM, Cloud Run and k8s/Knative targets. GCP = test target, never a structural dependency.
4. **Pluggable identity**: `AgentIdentityProvider` (oidc-mtls / spire / gcp optional). No generated agent depends on `gcp-agent-identity`.
5. **On top of `agents-cli`**: we delegate the generic ADK, we encode Dayuse's added value.
6. **GDPR**: EU residency, never a raw credential on the agent side (broker / Vault).
7. **HITL** mandatory on any write operation.

## Quick start

The skills trigger when you describe the need (no command to type). A typical journey:

1. **Scaffold a reusable leaf agent** — "scaffold me an MR writer agent" → `scaffold-agent`.
2. **Expose it over A2A** — "expose this agent over A2A" → `wire-a2a`.
3. **Scaffold an orchestrator that reuses it** — "create a logs → spec → fix → MR orchestrator" → `scaffold-orchestrator`.
4. **Deploy** — "deploy to Cloud Run and Knative" → `deploy-anywhere`.
5. **Evaluate** — "set up the evals for this agent" → `eval-agent`.

## License

Internal Dayuse — not publicly distributed.
