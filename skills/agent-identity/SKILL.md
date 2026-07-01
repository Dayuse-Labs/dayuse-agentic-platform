---
name: agent-identity
description: >
  Pluggable identity for Dayuse agents, without cloud lock-in. This skill should be used
  when a tech asks "how do agents authenticate", "agent identity", "mTLS / OIDC / SPIFFE /
  SPIRE", "AgentIdentityProvider", "avoid GCP dependency for identity", or when an agent
  must call another agent over A2A in an authenticated way. Provides the AgentIdentityProvider
  interface and its 3 implementations: oidc-mtls (portable default), spire (self-hosted
  production), gcp-agent-identity (optional, GCP only).
metadata:
  version: "0.1.0"
---

# Pluggable agent identity

Apply this contract whenever an agent must prove its identity (inbound/outbound A2A call, access to a token broker). The goal is for no agent to depend on a proprietary cloud identity service.

## Invariant

Identity **always** goes through the `AgentIdentityProvider` interface. The agent code depends on the **interface**, never on a concrete implementation. The provider is chosen at runtime via an environment variable:

```
DAYUSE_IDENTITY_PROVIDER=oidc-mtls   # default | spire | gcp-agent-identity
```

**Non-negotiable rule**: no generated agent imports or depends on `gcp-agent-identity`. This implementation can only be enabled on GCP, as an option, and remains interchangeable.

## The `AgentIdentityProvider` contract

A provider exposes at minimum:

- `get_identity()` → the identity of this agent (e.g. SPIFFE ID, OIDC subject, or GCP identity), in a neutral form.
- `get_outbound_credentials(audience)` → a **short-lived** credential (token/mTLS) to call the `audience` agent over A2A. Never a long-lived secret.
- `verify_inbound(request)` → validates the inbound A2A caller (mTLS + token + optional Agent Card signature); returns the verified identity or raises.
- `sign_agent_card(card)` / `verify_agent_card(card)` → JWS signing/verification of the Agent Card (JCS canonicalization) for integrity.

The interface skeleton (Python ABC/Protocol) and the three implementations are in `references/identity-providers.md`. Scaffolding copies this skeleton into the agent and exposes only the interface to business code.

## The 3 implementations

1. **`oidc-mtls` (portable default)** — mTLS between agents + signed A2A Agent Cards + OAuth2/OIDC via the Dayuse IdP. Works everywhere (Cloud Run, k8s, dev). Choose by default and for anything that is not self-hosted production.
2. **`spire` (self-hosted production target)** — SPIFFE/SPIRE: each agent receives an SVID (X.509 or JWT) attested by SPIRE. Choose in Dayuse self-hosted production, for strong identity without cloud dependency.
3. **`gcp-agent-identity` (optional)** — native GCP agent identity. **Can only be enabled on GCP**, never a dependency. Present for testing on GCP; interchangeable with the other two without touching business code.

## Wiring into the rest of the stack

- **A2A**: `verify_inbound` is called by the leaf's A2A server; `get_outbound_credentials` by the orchestrator before each hop. The accepted schemes are declared in the Agent Card (`securitySchemes`, OpenAPI 3 style). See `wire-a2a`.
- **Secrets**: the provider only issues short-lived credentials and delegates storage of long-lived secrets to the **token broker / Vault**. See `gdpr-guardrails`.
- **Portability**: identity is layer 4 of the stack (see `agent-architecture`).

## When you are asked to choose

By default, answer `oidc-mtls`. Recommend `spire` only if the context is explicitly self-hosted production. Only propose `gcp-agent-identity` if the agent runs on GCP **and** while reminding that it stays optional and interchangeable.

## Resources

- **`references/identity-providers.md`** — complete `AgentIdentityProvider` interface + skeleton of the 3 implementations + decision matrix.
