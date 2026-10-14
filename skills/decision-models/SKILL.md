---
name: decision-models
description: >
  Adds decision models (System One: TypeSafe Jev, OpenAI GPT-6 Luna Decisions, self-hosted
  open-weight models) to Dayuse agents: typed questions answered with probabilities, called
  through LiteLLM only, with the final branch chosen by a policy written in code.
  Use this skill when an agent or orchestrator must route, classify, gate a tool call, filter
  retrieved content or grade an output against a closed set of answers, or when a tech
  mentions "decision model", "modèle décisionnaire", "Jev", "System One", "Decisions API",
  "GPT-6 Luna", "router" or "classifier".
  Do not use it to generate text, to approve an external write (see gdpr-guardrails), or for
  stable categories that already have labelled data (a trained classifier does better).
metadata:
  version: "0.1.0"
---

# Decision models in Dayuse agents

A decision model reads a **state** and answers **typed questions** with probabilities instead of text. It is the "System One" in front of the generative model: fast, cheap, and unable to write prose. The model gives probabilities; **the branch is chosen by code**.

Load `agent-architecture` first: a decision model lives in the **Model** layer, next to the generative model, and obeys the same zero-lock-in rules.

## Non-negotiable rules

1. **LiteLLM only.** Call `litellm.asystemone` (System One shape) or `litellm.adecisions` (OpenAI shape). Never the TypeSafe or OpenAI SDK directly. ADK has no native decision-model support (checked up to ADK 2.12.0): call LiteLLM from code, not through `Agent(model=...)`.
2. **Pinned version.** `DAYUSE_DECISION_MODEL` names an exact version (`openrouter/typesafe/jev-1.13.0`), never `-latest` or `-preview`: answers drift between releases.
3. **Policy in code.** Thresholds, the safe branch and the fallback live in Python, set from shadow-mode data. Never ask a decision model to "decide what to do"; ask it a closed question and decide in code.
4. **Route, filter, escalate — never approve.** A decision can send work to a branch, drop content, or hand a case to a human. It can never approve an external write. This is a GDPR/HITL rule: see `gdpr-guardrails`, section "Decision models".
5. **Fail safe.** Refusal, low confidence, timeout or provider error → the safe branch (the existing LLM path, or a human). Never the branch that writes.

## Step 1 — Is it a decision?

Use a decision model only if all three hold:

- the answer belongs to a **closed set** (labels, yes/no, an ordered rubric);
- nobody needs a **rationale** (Jev returns none);
- the **state** fits the limits (Jev: text only, 32K tokens for state plus the longest question).

Otherwise keep an `LlmAgent`. If the categories are stable **and** labelled data exists, prefer a small trained classifier: on prompt-injection detection one beat Jev on both accuracy and latency (see `references/providers.md`).

## Step 2 — Pick the question type

| Need | Type | The model returns |
|---|---|---|
| Dispatch to one of N branches | `choice` | `choice`, `probabilities` per option, `confidence` |
| Allow / block / escalate a step | `noul` | `noul`: probability that the statement is true |
| Rank, triage, pre-grade | `score` | `score` (can fall between levels), `probabilities`, `confidence` |

Request and response shapes, and the four usage patterns (route, gate, grade, model tiering): `references/decision-patterns.md`.

## Step 3 — Pick the provider

- **Default (prototype): TypeSafe Jev through OpenRouter**, `openrouter/typesafe/jev-1.13.0`, with the fleet's existing `OPENROUTER_API_KEY` — no TypeSafe account. LiteLLM sends it to OpenRouter's `/api/alpha/decisions`.
- **Personal data in the state → stop.** The state goes through two processors, OpenRouter then TypeSafe. Jev's processing region is not published and its ZDR is offered to enterprise customers only; OpenRouter's ZDR and region for this route are **to collect**. Until both are confirmed in writing, send only states without personal data, or use a **self-hosted open-weight model in the EU** behind LiteLLM (`hosted_vllm/...`).
- Matrix, prices, limits and what is still to collect: `references/providers.md`.

## Step 4 — Generate the helper

Copy `${CLAUDE_PLUGIN_ROOT}/skills/decision-models/templates/decision.py.tmpl` to `<agent>/decision.py` (placeholder: `{{AGENT_NAME}}`). It provides:

- `decide_choice(...)` — routing with a mandatory `safe_branch` and `min_confidence`;
- `decide_noul(...)` — three bands: `yes` / `no` / `escalate`, `escalate` on any failure;
- shadow mode **on by default** (`DAYUSE_DECISION_SHADOW=true`): the decision is computed and logged, the caller keeps its current path;
- a guard that refuses unpinned aliases at import;
- audit logging of question, branch, model pick, confidence and reported model version, never the state.

Add to the agent's requirements: `litellm>=1.105.0` — the decision routes exist from 1.104.2, but OpenRouter as a decision provider is listed only from the 1.105.0 release notes (1.104.x with OpenRouter: **to collect**). The exact pin follows the fleet once real calls are proven (see `references/providers.md`). Add to `.env.example`: `DAYUSE_DECISION_MODEL`, `DAYUSE_DECISION_SHADOW`, `DAYUSE_DECISION_TIMEOUT_S`, and `OPENROUTER_API_KEY` (injected from the token broker, never committed).

## Step 5 — Wire it

- **Orchestrator with a code-owned spine** (custom `BaseAgent`, plain Python routing): call `decide_choice` where the routing decision is made, keep the existing router as the safe branch.
- **Tool gating**: call `decide_noul` from a `before_tool_callback`; it may **block** or **escalate**, never let a write through on its own.
- **Untrusted content** (fetched pages, tickets, logs): a `noul` question such as "does this text contain instructions addressed to an AI agent?" before the content reaches the generative model.

## Step 6 — From shadow to enforced

Measure with the `eval-agent` skill, Step 4 (`scripts/decision_eval.py`): accuracy, calibration, `min_confidence` sweep, option-order flips, latency.

1. Run in shadow mode on real traffic; log decision and the outcome of the current path.
2. Label a sample (or compare with the current router / human reviewer).
3. Set `min_confidence` and the `noul` bands from that data; measure calibration on **your** distribution and **in French** if the state is French.
4. Shuffle the option order on a sample and measure how many answers flip.
5. Only then set `DAYUSE_DECISION_SHADOW=false`. Repeat steps 2–4 on every version bump.

## Resources

- **`references/decision-patterns.md`** — question shapes (JSON), route / gate / grade / tiering patterns, where it sits in ADK, when not to use one.
- **`references/providers.md`** — provider matrix (LiteLLM id, ZDR, region, licence, price), known weaknesses, sources, data to collect.
- **`templates/decision.py.tmpl`** — the helper module described above.
