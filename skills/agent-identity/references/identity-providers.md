# `AgentIdentityProvider` — interface and implementations

Reference skeleton to copy into the generated agent (the `identity/` package). Business code depends only on `AgentIdentityProvider` and `get_identity_provider()`. The bodies marked `# TODO` are to be completed according to the Dayuse infrastructure, but the signatures and the env-variable wiring are fixed.

## Interface

```python
"""identity/provider.py — pluggable interface. DO NOT couple business code to an impl."""
from __future__ import annotations

import abc
import os
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AgentIdentity:
    """Neutral identity, independent of the provider."""
    subject: str            # SPIFFE ID, OIDC subject, or GCP identity — opaque form
    issuer: str
    claims: Mapping[str, Any]


class OutboundCredential:
    """SHORT-LIVED credential for an outbound A2A call (bearer token and/or mTLS context)."""
    def __init__(self, bearer: str | None = None, mtls_context: Any | None = None) -> None:
        self.bearer = bearer
        self.mtls_context = mtls_context


class AgentIdentityProvider(abc.ABC):
    """Pluggable identity contract. One implementation per strategy."""

    @abc.abstractmethod
    def get_identity(self) -> AgentIdentity:
        """Identity of THIS agent."""

    @abc.abstractmethod
    def get_outbound_credentials(self, audience: str) -> OutboundCredential:
        """Short-lived credential to call the `audience` agent over A2A. Never a long-lived secret."""

    @abc.abstractmethod
    def verify_inbound(self, request: Any) -> AgentIdentity:
        """Validates the inbound A2A caller (mTLS + token + signature). Returns the identity or raises."""

    @abc.abstractmethod
    def sign_agent_card(self, card: Mapping[str, Any]) -> Mapping[str, Any]:
        """Signs the Agent Card (JWS, JCS canonicalization) and returns the signed card."""

    @abc.abstractmethod
    def verify_agent_card(self, card: Mapping[str, Any]) -> bool:
        """Verifies the signature of a remote Agent Card."""


def get_identity_provider() -> AgentIdentityProvider:
    """Factory: chooses the implementation via DAYUSE_IDENTITY_PROVIDER (default: oidc-mtls)."""
    name = os.environ.get("DAYUSE_IDENTITY_PROVIDER", "oidc-mtls")
    if name == "oidc-mtls":
        from .oidc_mtls import OidcMtlsIdentityProvider
        return OidcMtlsIdentityProvider()
    if name == "spire":
        from .spire import SpireIdentityProvider
        return SpireIdentityProvider()
    if name == "gcp-agent-identity":
        # Optional, GCP only. Lazily imported: no hard dependency.
        from .gcp_agent_identity import GcpAgentIdentityProvider
        return GcpAgentIdentityProvider()
    raise ValueError(f"unknown DAYUSE_IDENTITY_PROVIDER: {name!r}")
```

The lazy import in the factory guarantees that **no GCP dependency** is loaded unless `gcp-agent-identity` is explicitly selected. Never import `gcp_agent_identity` elsewhere.

## `oidc-mtls` (portable default)

```python
"""identity/oidc_mtls.py — mTLS + OAuth2/OIDC (Dayuse IdP) + signed Agent Cards."""
import os
from typing import Any, Mapping
from .provider import AgentIdentityProvider, AgentIdentity, OutboundCredential


class OidcMtlsIdentityProvider(AgentIdentityProvider):
    def __init__(self) -> None:
        self.issuer = os.environ["DAYUSE_OIDC_ISSUER"]          # ex. https://idp.dayuse.io/
        self.client_id = os.environ["DAYUSE_OIDC_CLIENT_ID"]
        # Secret/key retrieved via the broker/Vault, not in clear text. See gdpr-guardrails.

    def get_identity(self) -> AgentIdentity:  # TODO: read the subject of the mTLS certificate / token
        ...

    def get_outbound_credentials(self, audience: str) -> OutboundCredential:
        # TODO: OAuth2 client_credentials (audience=target agent) + client mTLS context.
        ...

    def verify_inbound(self, request: Any) -> AgentIdentity:
        # TODO: validate the mTLS chain, verify the JWT (issuer, audience, exp) against the IdP.
        ...

    def sign_agent_card(self, card: Mapping[str, Any]) -> Mapping[str, Any]:
        # TODO: JWS (RFC 7515) over the JCS-canonicalized card (RFC 8785).
        ...

    def verify_agent_card(self, card: Mapping[str, Any]) -> bool:
        ...
```

## `spire` (self-hosted production, SPIFFE/SPIRE)

```python
"""identity/spire.py — X.509/JWT SVID attested by SPIRE via the Workload API."""
import os
from typing import Any, Mapping
from .provider import AgentIdentityProvider, AgentIdentity, OutboundCredential


class SpireIdentityProvider(AgentIdentityProvider):
    def __init__(self) -> None:
        # SPIFFE Workload API socket, e.g. unix:///run/spire/sockets/agent.sock
        self.workload_api = os.environ["SPIFFE_ENDPOINT_SOCKET"]

    def get_identity(self) -> AgentIdentity:        # TODO: retrieve the SPIFFE ID via py-spiffe
        ...

    def get_outbound_credentials(self, audience: str) -> OutboundCredential:
        # TODO: JWT SVID (aud=audience) or X.509-SVID mTLS context.
        ...

    def verify_inbound(self, request: Any) -> AgentIdentity:
        # TODO: validate the peer SVID via the SPIFFE trust bundle.
        ...

    def sign_agent_card(self, card: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    def verify_agent_card(self, card: Mapping[str, Any]) -> bool:
        ...
```

## `gcp-agent-identity` (optional, GCP only)

```python
"""identity/gcp_agent_identity.py — OPTIONAL. Can only be enabled on GCP.
No other part of the code should import this module; it is lazily loaded
by the factory only if DAYUSE_IDENTITY_PROVIDER=gcp-agent-identity."""
from typing import Any, Mapping
from .provider import AgentIdentityProvider, AgentIdentity, OutboundCredential


class GcpAgentIdentityProvider(AgentIdentityProvider):
    def __init__(self) -> None:
        ...  # TODO: GCP dependencies isolated here, never at the shared module level.

    def get_identity(self) -> AgentIdentity: ...
    def get_outbound_credentials(self, audience: str) -> OutboundCredential: ...
    def verify_inbound(self, request: Any) -> AgentIdentity: ...
    def sign_agent_card(self, card: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def verify_agent_card(self, card: Mapping[str, Any]) -> bool: ...
```

## Decision matrix

| Context | Provider | Why |
|---|---|---|
| Default, dev, multi-cloud, Cloud Run | `oidc-mtls` | Portable, mTLS + OIDC via Dayuse IdP, zero cloud dependency |
| Self-hosted production (k8s/Knative) | `spire` | Strong attested identity, without cloud |
| Testing on GCP | `gcp-agent-identity` | Convenient on GCP, **stays optional and interchangeable** |

Review rule: if an agent imports anything from `gcp_agent_identity` outside the factory, **block it**.
