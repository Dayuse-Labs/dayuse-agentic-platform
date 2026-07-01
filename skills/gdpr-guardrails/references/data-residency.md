# GDPR, token broker & HITL contract (detail)

## GDPR checklist (per agent, to clear before deployment)

1. Runtime deployed in an **EU region** (Cloud Run / k8s / Knative).
2. Every MCP/tool handling personal data is hosted/configured in the EU.
3. **Minimization**: only the necessary data is passed to the agent/leaf.
4. No superfluous personal data in logs, specs, prompts.
5. Model provider (via LiteLLM) with an endpoint/region compatible with EU residency.
6. A "data: nature, transit, residency, retention" section present in the agent's README.
7. No long-lived secret in the image or a committed file.

## Token broker / Vault

The agent never reads a long-lived secret. It requests a short-lived, minimally scoped token from the broker:

```python
"""secrets/broker.py — secret access via broker/Vault, never in plaintext."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ShortLivedToken:
    value: str
    expires_at: float        # epoch ; the token is short-lived (minutes)
    scope: str               # minimal privilege, e.g. "gitlab:write:mr"


class TokenBroker:
    def __init__(self) -> None:
        self.endpoint = os.environ["DAYUSE_TOKEN_BROKER_URL"]   # e.g. Vault / internal IdP
        # The agent's auth TO the broker goes through AgentIdentityProvider (mTLS/OIDC/SPIFFE).

    def fetch(self, scope: str) -> ShortLivedToken:
        """Exchange the agent's identity for a short-lived token for `scope`."""
        ...  # TODO: Vault/broker call authenticated by the agent's identity
```

Rules: short lifetime, minimal scope, on-demand renewal, never a persistent on-disk cache.

## HITL checkpoint contract

Every write tool is preceded by a confirmation step. Expected shape of the preview presented to the human:

- **MR**: project, source → target branch, title, description, summarized **diff**.
- **GitLab issue**: project, title, labels, body.
- **Notion**: target page/database, title, content excerpt.

Pseudo-implementation on the agent side (the plugin hook is the safety belt; this is the suspenders):

```python
def commit_write(preview: dict, do_write):
    show_to_human(preview)                 # show the preview
    if not ask_human_confirmation():       # explicit "yes" required
        log_audit("write.cancelled", preview)
        return {"status": "cancelled"}
    result = do_write()                    # actual write (MR/issue/Notion)
    log_audit("write.committed", {**preview, "by": current_human()})
    return {"status": "committed", "result": result}
```

## Audit

Log at minimum: action type, target, agent identity, human approver identity, timestamp, result. Keep these logs in the EU, without superfluous personal data.

## Anti-patterns to block in review

- Write (MR/issue/Notion) without a human confirmation step.
- Long-lived secret mounted into the image / committed / cached on disk.
- Personal data copied into logs or prompts without necessity.
- Runtime or tool outside the EU for personal data.
