---
name: eval-agent
description: >
  Sets up the ADK evaluation harness for a Dayuse agent/orchestrator with a starter test
  set. This skill triggers when a tech wants to "evaluate an agent", "create agent tests",
  "an ADK evalset", "check agent quality", or validate the Dayuse invariants (HITL, LiteLLM,
  zero GCP dependency). Delegates the generic ADK harness to google-agents-cli-eval and adds
  the Dayuse cases and guardrails.
metadata:
  version: "0.1.0"
---

# Evaluate a Dayuse agent

Set up evaluation tooling so an agent is tested on its **function** and on the **Dayuse invariants**. Delegate the generic ADK harness to `agents-cli`; this skill adds the Dayuse layer.

## Step 1 — Delegate the generic harness

Let `agents-cli` lay down the standard ADK evaluation harness (`adk eval`, evalset format, criteria config). Do not duplicate that knowledge.

## Step 2 — Starter functional cases

Create an evalset (see `references/eval-harness.md`) with a few cases covering the agent's role: representative inputs, expected tool trajectory, and reference response. For an orchestrator, test the end-to-end pipeline with simulated or test A2A leaves.

## Step 3 — "Dayuse invariants" cases

Add cases that fail if an invariant is violated:

- **HITL**: on a write request (MR/issue/Notion), the agent must **show a preview and ask for confirmation**, never write silently. The case verifies that no write tool is called without a confirmation step.
- **Identity**: the agent advertises/uses `oidc-mtls` (or `spire`); no path requires `gcp-agent-identity`.
- **Model**: the provider goes through LiteLLM (`DAYUSE_MODEL`).

## Step 4 — Static guardrail (zero lock-in)

In addition to the behavioral evals, copy the **static check** shipped in `${CLAUDE_PLUGIN_ROOT}/skills/eval-agent/scripts/dayuse_guardrails.sh` into the project's `scripts/` and run it. It fails if the generated code:

- imports `gcp_agent_identity` anywhere other than the `get_identity_provider()` factory;
- imports a hardcoded cloud model SDK (instead of LiteLLM);
- contains a write without a detectable HITL checkpoint.

This check satisfies the criterion "no generated file introduces a hard dependency on GCP".

## Step 5 — Criteria & execution

Define the thresholds (tool trajectory, response match) then run:

```
adk eval <agent_path> <evalset.evalset.json> --config_file_path test_config.json
```

## Step 6 — Wire into CI

Wire the eval **and** the static guardrail into the GitLab CI (see the snippet in the reference) so no regression or forbidden dependency makes it into an MR. Every GitLab commit goes through HITL.

## Resources

- **`references/eval-harness.md`** — ADK evalset skeleton, starter cases (functional + invariants), GitLab CI snippet.
- **`scripts/dayuse_guardrails.sh`** — zero lock-in static guardrail, ready to copy into the project's `scripts/`.
