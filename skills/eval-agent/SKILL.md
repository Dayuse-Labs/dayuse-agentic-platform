---
name: eval-agent
description: >
  Sets up the ADK evaluation harness for a Dayuse agent/orchestrator with a starter test
  set. This skill triggers when a tech wants to "evaluate an agent", "create agent tests",
  "an ADK evalset", "check agent quality", "evaluate a decision model", "set a confidence
  threshold", or validate the Dayuse invariants (HITL, LiteLLM, zero GCP dependency).
  Delegates the generic ADK harness to google-agents-cli-eval and adds the Dayuse cases,
  the decision-point evaluation and the guardrails.
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

## Step 4 — Decision points (if the agent uses a decision model)

A decision point is code calling a decision model (`decision-models` skill), not an `LlmAgent`: `adk eval` does not measure it. Measure it with `${CLAUDE_PLUGIN_ROOT}/skills/eval-agent/scripts/decision_eval.py` (copy it into the project's `scripts/`) before `DAYUSE_DECISION_SHADOW=false`, and again on every change of `DAYUSE_DECISION_MODEL`.

1. **Labelled cases** — `cases.jsonl`, one `{"id", "state", "label"}` per line, taken from shadow-mode traffic and labelled by a human (or by the current router where it is trusted). Cover every option; the report shows per-label counts, so a thin label is visible. **No personal data** when the provider is not self-hosted in the EU: the script refuses to run without `--no-personal-data` (gdpr-guardrails §4).
2. **The question** — `question.json`, the exact `name`, `type`, `instructions` and `options` the agent sends. Measuring a different wording measures a different decision.
3. **Run** — `python decision_eval.py --cases cases.jsonl --question question.json --out decision-report.md --raw decision-raw.jsonl` (+ `--no-personal-data` for Jev).
4. **Read the report**:
   - accuracy and per-label recall (refusals and errors count as misses);
   - calibration: 10 bins and the expected calibration error — is a 0.9 really right 9 times out of 10 on *our* data?
   - the `min_confidence` sweep: coverage vs accuracy when enforced. Pick the threshold there, write it in the code with the report's date and model version;
   - option order: share of answers that change when the options are reversed (choice only);
   - refusals, errors, latency P50/P95 of this run, and the model version(s) that answered (more than one = the numbers mix versions).
5. **Gate** — attach the report to the MR that sets `DAYUSE_DECISION_SHADOW=false`. The calls cost money and need a provider key: run it by hand or in a manual CI job, never on every push.

## Step 5 — Static guardrail (zero lock-in)

In addition to the behavioral evals, copy the **static check** shipped in `${CLAUDE_PLUGIN_ROOT}/skills/eval-agent/scripts/dayuse_guardrails.sh` into the project's `scripts/` and run it. It fails if the generated code:

- imports `gcp_agent_identity` anywhere other than the `get_identity_provider()` factory;
- imports a hardcoded cloud model SDK (instead of LiteLLM);
- lets the MR-review exemption (R2) spread: the unattended approver named outside
  `agents/mr_commenter`, or another agent calling `commit_write` without a human approver.

- calls a decision model outside LiteLLM (vendor SDK, raw `/v1/systemone`, `/v1/decisions` or OpenRouter `/api/alpha/decisions` URL, `typesafe-sdk` dependency);
- names an unpinned decision model (`jev-latest`, `jev-preview`, `DAYUSE_DECISION_MODEL=…-latest`);
- asks a decision model and calls `commit_write` in the same module (a decision routes or escalates, never approves a write). Tests are skipped. A decision in one module feeding a write in another is invisible to grep: that is the auditor's job.

This check satisfies the criterion "no generated file introduces a hard dependency on GCP".

## Step 6 — Criteria & execution

Define the thresholds (tool trajectory, response match) then run:

```
adk eval <agent_path> <evalset.evalset.json> --config_file_path test_config.json
```

## Step 7 — Wire into CI

Wire the eval **and** the static guardrail into the GitLab CI (see the snippet in the reference) so no regression or forbidden dependency makes it into an MR. Every GitLab commit goes through HITL.

## Resources

- **`references/eval-harness.md`** — ADK evalset skeleton, starter cases (functional + invariants), decision-eval input files, GitLab CI snippet.
- **`scripts/decision_eval.py`** — decision-point measurement (accuracy, calibration, threshold sweep, option order, latency) through LiteLLM; never writes the state.
- **`scripts/dayuse_guardrails.sh`** — zero lock-in static guardrail, ready to copy into the project's `scripts/`.
