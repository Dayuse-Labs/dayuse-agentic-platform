---
name: agent-architecture
description: >
  Mental model of Dayuse's modular agentic architecture. This skill should be used
  when a technical team member asks "how to structure an agent", "orchestrator or
  simple agent?", "when to share an agent", "our A2A architecture", "the Dayuse
  portability stack", or before any agent/orchestrator scaffolding. Loads the Dayuse
  conventions: orchestrator vs A2A leaf agent, sharing rules, 4-layer portability
  stack, the "pluggable identity" reminder, and delegation of generic ADK matters to
  the google-agents-cli-* skills.
metadata:
  version: "0.1.0"
---

# Dayuse agentic architecture

Load this mental model before designing, scaffolding, or reviewing an agent or an orchestrator. It sets the vocabulary and the invariants; the other skills (`scaffold-agent`, `scaffold-orchestrator`, `wire-a2a`, `agent-identity`, `gdpr-guardrails`, `deploy-anywhere`, `eval-agent`) build on it.

## Founding invariant

Always distinguish **two roles**, never to be conflated:

- **Leaf agent**: a specialized agent (coder, tester, MR writer, spec generator, spec evaluator…). Deployed **only once**, exposed over A2A, reused by several orchestrators. It does **one thing** and accesses its tools via MCP.
- **Orchestrator**: an agent that decomposes an end-to-end intent (e.g. "logs → spec → fix → MR", "Notion ticket → spec → fix → MR") and **calls leaf agents over A2A**. It does not reimplement their logic; it composes them.

Rule: an orchestrator calls leaf agents **over A2A**; an agent (leaf or orchestrator) calls tools **over MCP**. A2A = agent↔agent. MCP = agent↔tool.

## When to share an agent (deploy a reusable leaf)

Create an independently deployed leaf agent when **at least two** are true:

1. The capability is reused by **≥ 2 orchestrators**, current or foreseeable (e.g. "write an MR" serves both the logs flow and the Notion ticket flow).
2. The capability has a **stable contract** expressible as an A2A Agent Card (clear inputs/outputs).
3. The capability has its **own life cycle or secrets** (e.g. GitLab write access) that we want to isolate behind an A2A + identity boundary.

Otherwise, keep the logic **inline** in the orchestrator (local ADK sub-agent, no separate deployment). Do not over-fragment: one A2A agent = one network boundary, one identity, one deployment to maintain.

Before scaffolding, **always** check whether an equivalent leaf already exists (see `scaffold-orchestrator`, which consults the agent registry before generating a new one).

## 4-layer portability stack

Every Dayuse agent is portable because no layer depends hard on a cloud. From the bottom up:

1. **Model** — always via **LiteLLM**. We keep Claude behind it, but the code never references a proprietary model SDK. Changing provider = changing an env variable, not the code.
2. **Execution** — **OCI container systematically**. Supported targets: **Cloud Run** (= containers, non-blocking) and **Kubernetes/Knative**. No proprietary cloud API in the agent code.
3. **Coordination** — **A2A** (orchestrator→leaves, signed Agent Cards) + **MCP** (agent→tools: GitLab, Notion, logs, MySQL, Elasticsearch, RabbitMQ, Sentry…). The business MCP servers are wired into the agent, never into this plugin.
4. **Identity & secrets** — pluggable **`AgentIdentityProvider`** interface (`oidc-mtls` by default, `spire`, optional `gcp-agent-identity`) + **token broker / Vault**: never a raw credential on the agent side.

Detail and trade-offs: see `references/portability-stack.md`.

## "Pluggable identity" reminder

GCP is a **test target, never a structural dependency**. No generated agent should import or depend on `gcp-agent-identity`. Identity always goes through the `AgentIdentityProvider` interface; the portable default is `oidc-mtls`. For any agent↔agent authentication question, load the `agent-identity` skill.

## GDPR by construction

Data residency in **Europe**. **Mandatory human-in-the-loop** on every write operation (MR push, GitLab issue creation, Notion write) — a hook enforces it, but the design must anticipate it. Details: `gdpr-guardrails` skill.

## We sit ON TOP OF `agents-cli`

This plugin **does not teach** generic ADK. For raw ADK scaffolding, agent patterns, evaluation, and standard deployment, **delegate to the Google `google-agents-cli-*` skills**. This plugin encodes only the **Dayuse added value**: conventions, portability/identity strategy, guardrails, and skills that orchestrate `google-agents-cli-*` with our defaults. If those skills are not installed, flag it and point to the README.

**Authoritative ADK docs**: for any question about the ADK API or ADK/A2A patterns, prefer the embedded **`adk-docs`** MCP (official source `adk.dev/llms.txt`) — tools `list_doc_sources` then `fetch_docs`. `context7` remains the fallback and covers the rest of the stack (LiteLLM, MCP protocol, uvicorn…).

## Deciding: leaf, orchestrator, or inline?

Follow this order:

1. Does the capability already exist as an A2A leaf? → **reuse** it (`scaffold-orchestrator`).
2. Otherwise, does it meet ≥ 2 sharing criteria? → deployed **leaf agent** (`scaffold-agent` then `wire-a2a`).
3. Otherwise → **inline** in the orchestrator.

Concrete orchestration patterns (sequential, parallel, routing, spec↔eval loop): see `references/orchestrator-patterns.md`.

## Resources

- **`references/portability-stack.md`** — the 4 layers in detail, trade-offs, lock-in anti-patterns.
- **`references/orchestrator-patterns.md`** — orchestrator↔leaves patterns, examples of the "logs → MR" and "Notion ticket → MR" flows.
