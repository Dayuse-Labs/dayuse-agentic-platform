# Deployment targets (same image, zero lock-in)

Principle: **a single OCI image** deployable to all targets. The target changes neither the code, nor the model provider (LiteLLM), nor the identity (`AgentIdentityProvider`).

## Cloud Run (TEST target)

Cloud Run is just a container runtime that consumes the **Knative Serving** API. Handy for testing; **never** a structuring dependency.

```
gcloud run services replace service.cloudrun.yaml --region europe-west1
```

Rules:

- **EU** region (`europe-west1`, etc.) for residency.
- Secrets injected via the secret manager (references), not in the manifest.
- No GCP-only annotation essential to operation: the agent must remain deployable elsewhere without modification.

## Kubernetes / Knative (self-hostable prod target)

Same image, Knative `Service` manifest:

```
kubectl apply -f service.knative.yaml
# or with the Knative CLI:
kn service create <name> --image ${DAYUSE_REGISTRY}/agents/<name>:<tag> --port 8080
```

Without Knative, a classic k8s `Deployment` + `Service` also works (the agent listens on `$PORT`).

## Comparison

| Aspect | Cloud Run | k8s / Knative |
|---|---|---|
| Role | test target | self-hosted prod target |
| API | Knative Serving (managed) | Knative / k8s |
| Image | identical | identical |
| Scale to 0 | yes | yes (Knative) |
| Structuring dependency | **no** (forbidden) | no |

## Deployment checklist

1. Same image as the other targets (`${DAYUSE_REGISTRY}/agents/<name>:<tag>`).
2. The container listens on `$PORT`, non-root, with no cloud metadata server.
3. Model provider via LiteLLM (`DAYUSE_MODEL`).
4. Secrets via the target's manager, EU region.
5. No essential GCP dependency; `gcp-agent-identity` absent from the image.
