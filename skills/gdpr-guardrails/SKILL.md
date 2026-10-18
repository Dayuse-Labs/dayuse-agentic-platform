---
name: gdpr-guardrails
description: >
  GDPR and human-in-the-loop guardrails for the Dayuse agentic platform. This skill should
  be used when a tech asks "is this GDPR-compliant", "data residency",
  "token broker / Vault", "HITL", "human approval before writes", or whenever
  an agent performs a write operation (MR push, GitLab issue creation,
  Notion write), or when a decision model sits next to a write or receives personal data.
  Encodes: data residency in Europe (EU), token broker (no raw credentials on the agent
  side), mandatory HITL on every write, decision models that route but never approve.
metadata:
  version: "0.2.0"
---

# GDPR & HITL Guardrails

Apply these rules to the design **and** the execution of every Dayuse agent. They are not optional; a plugin `PreToolUse` hook enforces HITL, but the design must anticipate it.

## 1. Data residency — Europe

- All processing and storage of personal data stays in **Europe (EU)**. Choose EU regions for the runtime (Cloud Run, k8s/Knative) and for any MCP/tool handling personal data.
- **Minimization**: pass an agent/leaf only the data it needs for its task. Do not copy personal data into logs, specs, or prompts unless it is indispensable.
- For each generated agent, document where its data transits and resides (a dedicated section of the agent's README).
- The model provider goes through LiteLLM; verify that the provider's region/endpoint complies with EU residency.

## 2. No raw credentials on the agent side — token broker / Vault

- An agent **never holds** a long-lived secret (API key, PAT, password). It obtains **short-lived tokens** through a **token broker / Vault** (the portable equivalent of the "Auth Manager").
- Outbound credentials for A2A calls come from `AgentIdentityProvider.get_outbound_credentials()` (see `agent-identity`), not from plaintext variables persisted somewhere.
- Tool access (GitLab, Notion…) uses tokens injected at runtime from the broker/Vault, with minimal privilege and short lifetime.
- **Anti-pattern**: mounting a long-lived service key into the image or a committed `.env`.

## 3. Mandatory human-in-the-loop on writes

Every **write operation** requires **explicit human confirmation** before execution. This notably covers:

- **Merge Request push / creation / update** (GitLab).
- **GitLab issue creation / modification**.
- **Notion write** (page creation/edit, comment).
- More generally: any action that modifies an external system.

Expected mechanics (on the agent side **and** guaranteed by the plugin's `PreToolUse` hook):

1. The agent **prepares** the write and presents a **preview** of it (MR diff, issue title+body, Notion content).
2. It **stops** and asks the human for approval. No auto-merge, no silent write.
3. The write happens only after an **explicit "yes"**. A refusal cancels it cleanly.
4. The action and its author (the human approver) are **logged** for audit.

Design flows so that the write is **the last step**, isolated in a dedicated leaf (`mr-writer`, etc.), so that the HITL checkpoint is single and clear.

### Exemptions: numbered, argued, enforced — never implicit

HITL is the default and stays the default: a **new** write leaf is gated, and a design that skips
the checkpoint without an exemption is wrong. But the rule admits exemptions, and the shape of a
legitimate one matters more than the list:

1. **Numbered and written down** in the fleet's HITL register (`dayuse-agent-fleet/README.md`), with
   the date and who granted it. An exemption nobody can cite does not exist.
2. **Argued from reversibility**, not from convenience. The question is what a wrong write costs to
   undo. An MR review comment can be deleted; a created ticket, a Notion page or a merged MR
   propagates — notifications, someone's inbox, a downstream process. Friction is a reason to ask
   for an exemption, never a reason to grant one.
3. **Narrowest possible scope** — one named agent, one kind of write. Not "GitLab writes".
4. **Compensating guards named explicitly**, replacing what the human was doing. If nothing
   replaces the human, the answer is no.
5. **Statically enforced** so it cannot spread: the fleet's `scripts/dayuse_guardrails.sh` fails the
   build if the exempt agent's auto-approver appears anywhere else, or if another agent calls
   `commit_write` without a human approver.
6. **Still through `commit_write()`**, so the audit line survives — with the approving *surface*
   recorded, never anything that reads like a person.

Two exist today: **R1** (the fixer's `agent/<task_id>` branch push — branch scope only, CI needs it)
and **R2** (`mr_commenter`'s MR **review comments**, 2026-09-02 — the worked example of all six
points above). Everything else asks a human.

## 4. Decision models: route, never approve

A decision model (System One, see `decision-models`) answers closed questions with probabilities. Its place relative to HITL is fixed:

1. **It never approves an external write.** Not as the HITL checkpoint, not as the approving surface of an exemption, not "because confidence is high". A probability is not a person.
2. **It can make things stricter, never looser.** It may route work to a flow (whose write still passes its own checkpoint), drop untrusted content, block a step, or escalate to a human. A "no objection" from a decision gate is not a permission.
3. **Failure goes to the safe side.** Refusal, low confidence, timeout or provider error → the existing path or a human, never the branch that writes.
4. **In an exemption, one guard among others.** A decision model may appear in the compensating guards of a numbered exemption only next to at least one code-owned blocker, and never as the approving surface.
5. **The `state` is a data transfer.** Minimization applies to it as to any prompt. Dayuse calls Jev through OpenRouter, so the state crosses **two processors**. Jev's processing region is not published and its ZDR is offered to enterprise customers only; OpenRouter's ZDR and region for this route are still to collect. Until both are confirmed in writing for both processors, **no personal data in a Jev state**. States with personal data go to a self-hosted EU decision model.
6. **Audit without the state.** Log question, chosen branch, model pick, confidence and the model version the provider reports, never the raw state.

## 5. Traceability

- Log every A2A hop and every write tool call (who, what, when, approved by whom).
- Do not log superfluous personal data (cf. minimization).

## When scaffolding or reviewing

- `scaffold-agent` / `scaffold-orchestrator`: insert the HITL checkpoint before any write and wire up the token broker.
- Review: if an agent writes without a confirmation step **and without a numbered exemption meeting the six conditions above**, or holds a long-lived secret, **block it**.
- Review: if a decision model's output is used as an approval, or is the only compensating guard of an exemption, or receives personal data from a provider whose ZDR and region are not confirmed, **block it**.

## Resources

- **`references/data-residency.md`** — GDPR checklist, token broker diagram, HITL checkpoint contract, write preview examples.
