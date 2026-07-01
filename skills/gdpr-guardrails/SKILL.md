---
name: gdpr-guardrails
description: >
  GDPR and human-in-the-loop guardrails for the Dayuse agentic platform. This skill should
  be used when a tech asks "is this GDPR-compliant", "data residency",
  "token broker / Vault", "HITL", "human approval before writes", or whenever
  an agent performs a write operation (MR push, GitLab issue creation,
  Notion write). Encodes: data residency in Europe (EU), token broker (no raw
  credentials on the agent side), mandatory HITL on every write.
metadata:
  version: "0.1.0"
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

## 4. Traceability

- Log every A2A hop and every write tool call (who, what, when, approved by whom).
- Do not log superfluous personal data (cf. minimization).

## When scaffolding or reviewing

- `scaffold-agent` / `scaffold-orchestrator`: insert the HITL checkpoint before any write and wire up the token broker.
- Review: if an agent writes without a confirmation step, or holds a long-lived secret, **block it**.

## Resources

- **`references/data-residency.md`** — GDPR checklist, token broker diagram, HITL checkpoint contract, write preview examples.
