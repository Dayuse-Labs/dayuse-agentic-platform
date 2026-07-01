---
name: deploy-anywhere
description: >
  Containerizes and deploys a Dayuse agent/orchestrator anywhere, with no hard dependency
  on the cloud. This skill triggers when a tech wants to "deploy an agent", "containerize",
  "publish to Cloud Run", "deploy to Kubernetes/Knative", or talks about deployment
  portability. Delegates generic ADK deployment to google-agents-cli-deploy; adds the Dayuse
  zero-lock-in overlay: one same OCI image → Cloud Run + k8s/Knative, model provider
  abstracted via LiteLLM. GCP is only a test target.
metadata:
  version: "0.1.0"
---

# Deploy anywhere

Ship a portable agent: **one image, multiple targets**. First load `agent-architecture` (portability stack, layers 1–2).

## Step 1 — Verify the container

Make sure the agent has a portable `Dockerfile` (produced by `scaffold-agent`):

- listens on `$PORT` (default 8080);
- starts **without** a cloud metadata server;
- runs as a non-root user;
- embeds no secret.

If missing, generate it before continuing.

## Step 2 — Build & publish the image

Build the OCI image and push it to a registry **driven by an env variable** (`DAYUSE_REGISTRY`), never a hard-coded cloud registry:

```
docker build -t ${DAYUSE_REGISTRY}/agents/<name>:<tag> .
docker push ${DAYUSE_REGISTRY}/agents/<name>:<tag>
```

The **same image** serves all targets.

## Step 3 — Abstract the model (LiteLLM)

Confirm the provider goes through LiteLLM (`DAYUSE_MODEL`). Switching deployment target must never force switching provider or code.

## Step 4 — Choose the target & generate the manifest

Read the appropriate template from `${CLAUDE_PLUGIN_ROOT}/skills/deploy-anywhere/templates/` and substitute `{{AGENT_NAME}}`, `{{IMAGE}}`, `{{TAG}}`:

- **Cloud Run** (`service.cloudrun.yaml.tmpl`) — **test** target, non-blocking. Cloud Run consumes the Knative Serving API.
- **Kubernetes / Knative** (`service.knative.yaml.tmpl`) — self-hostable prod target.

Commands and comparison: `references/targets.md`.

## Step 5 — Inject the configuration (never in the image)

Provide the configuration via env variables / the target's secret manager:

- `DAYUSE_MODEL`, `DAYUSE_IDENTITY_PROVIDER` (default `oidc-mtls`), `DAYUSE_TOKEN_BROKER_URL`, business MCP URLs, `AGENT_PUBLIC_URL`.
- Secrets (`ANTHROPIC_API_KEY`, tokens) from the target's secret manager, **never** in the image or the committed manifest.
- **EU** region for data residency.

## Step 6 — Invariants

- **GCP = test target, never a structuring dependency.** The Cloud Run manifest must contain no GCP-only annotation essential to operation.
- No `gcp-agent-identity` import/dependency in the image.
- Run through the zero-lock-in checklist again (`agent-architecture/references/portability-stack.md`).

## Step 7 — Guardrails

Deployment is a sensitive operation: confirm (HITL) before an `apply`/`replace` that pushes to a shared environment. Every GitLab commit of a manifest goes through HITL.

## Resources

- **`references/targets.md`** — Cloud Run vs k8s/Knative commands, the "same image" principle, the GCP test-only posture.
- **`templates/service.cloudrun.yaml.tmpl`**, **`templates/service.knative.yaml.tmpl`**.
