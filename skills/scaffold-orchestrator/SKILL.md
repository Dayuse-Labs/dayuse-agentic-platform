---
name: scaffold-orchestrator
description: >
  Scaffolds a Dayuse orchestrator and its set of A2A leaf agents, reusing the agents
  already deployed. This skill triggers when a tech wants to "create an orchestrator",
  "an agent pipeline", "a logs → spec → fix → MR flow" or "Notion ticket → spec →
  fix → MR", or compose several agents. Delegates the generic ADK skeleton and workflow
  patterns to google-agents-cli-scaffold / google-agents-cli-workflow; adds the Dayuse
  value: end-to-end decomposition, reuse of existing leaves (RemoteA2aAgent), and HITL
  on the final write. For a single agent, use scaffold-agent.
metadata:
  version: "0.1.0"
---

# Scaffold a Dayuse orchestrator

Produce a portable ADK orchestrator that **composes A2A leaf agents** without reimplementing their logic. Maximize **reuse**.

## Step 0 — Frame (load the mental model)

Load `agent-architecture`. Restate the end-to-end intent as a sequence of **capabilities** (subtasks), e.g. for "logs → spec → fix → MR": generate-spec, (evaluate-spec), code-fix, test, write-MR.

## Step 1 — Check `agents-cli`

Check for the presence of the `agents-cli` skills (generic ADK skeleton). If they are missing, flag it and point to the README, then continue best-effort.

## Step 2 — Reuse before creating (the key point)

For **each capability**, consult the **leaf-agent registry**: read `agents-registry.yaml` at the platform repo root (schema + bootstrap in `references/reuse-registry.md`; seed template at `${CLAUDE_PLUGIN_ROOT}/skills/scaffold-orchestrator/templates/agents-registry.yaml.tmpl`). If it does not exist yet, create it from that template (empty list — the ecosystem is empty on day one), then:

1. **An equivalent leaf already exists** → **reuse** it: declare a `RemoteA2aAgent` pointing at its Agent Card URL (`.../.well-known/agent-card.json`). **Regenerate nothing.**
2. **No leaf, but ≥ 2 sharing criteria met** (see `agent-architecture`) → scaffold a **new leaf** with `scaffold-agent`, deploy it, register it in the registry, then reference it.
3. **Otherwise** → keep the logic **inline** in the orchestrator (local ADK sub-agent).

This is the central goal: an agent deployed **once** serves several orchestrators. The "logs → MR" and "Notion ticket → MR" flows share the same leaves (only the input differs).

## Step 3 — Choose the composition pattern

Select based on the shape of the work (see `agent-architecture/references/orchestrator-patterns.md`): **sequential** (pipeline), **parallel** (fan-out/in), **routing** (dispatch), **loop** (spec ↔ eval, bounded). Always bound loops and call depths.

## Step 4 — Generate the orchestrator (template)

Read `${CLAUDE_PLUGIN_ROOT}/skills/scaffold-orchestrator/templates/orchestrator_agent.py.tmpl`, substitute the placeholders, and compose the leaves (reused `RemoteA2aAgent`s + any new ones + inline sub-agents). The orchestrator is itself a portable agent: reuse the Dayuse overlay from `scaffold-agent` (LiteLLM, `identity/`, `serve.py`, `Dockerfile`, `requirements.txt`, `.env.example`).

## Step 5 — Identity & guardrails

- **Authenticated A2A**: the orchestrator obtains its outbound credentials via `identity.get_outbound_credentials(audience)` for each leaf; the leaves validate via `verify_inbound`. See `agent-identity`.
- **HITL**: the final write (MR/issue/Notion) is isolated in a dedicated leaf (e.g. `mr_writer`) and triggers human confirmation. Design the pipeline so the write is the **last** step, a single control point.
- **GDPR**: data minimization between steps, EU residency. See `gdpr-guardrails`.

## Step 6 — Invariants & next steps

- Re-run the zero-lock-in checklist (`agent-architecture/references/portability-stack.md`).
- Propose: `deploy-anywhere` (manifests), `eval-agent` (end-to-end eval), `wire-a2a` (if a new leaf must be exposed).
- Every GitLab commit (branch/MR) of the scaffold goes through **HITL**.

## Resources

- **`references/reuse-registry.md`** — leaf registry convention, how to search for an existing leaf (registry + GitLab), how to register a new leaf.
- **`templates/orchestrator_agent.py.tmpl`** — orchestrator skeleton composing `RemoteA2aAgent`s.
- **`templates/agents-registry.yaml.tmpl`** — seed for `agents-registry.yaml` (schema + commented example); copy it to the platform repo root on day one.
