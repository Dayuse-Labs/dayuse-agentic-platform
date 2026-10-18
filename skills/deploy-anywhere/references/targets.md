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
| https between agents | native (`run.app`) | to set up (see below) |
| Structuring dependency | **no** (forbidden) | no |

## A2A transport per target (https off loopback)

ADK ≥ 2.7 refuses a card URL, or a card `url`, in plain `http` outside loopback, and requires the card's `url` to share the card URL's origin. Rule and sources: `wire-a2a/references/agent-card-spec.md` § Transport.

| Target | Default service-to-service URL | Refused by ADK ≥ 2.7? | Compliant setup |
|---|---|---|---|
| Cloud Run | `https://<service>-….run.app` | no | Nothing to add. Every service has a stable HTTPS URL; Cloud Run redirects HTTP to HTTPS and terminates TLS before the container. `AGENT_PUBLIC_URL` = that URL. |
| k8s / Knative | `http://<svc>.<ns>.svc.cluster.local` | **yes** | Knative `cluster-local-domain-tls`: the cluster-local URL becomes https. Experimental, Kourier or Istio only, needs cert-manager, and callers must trust the CA. Or reach the leaf through an https ingress / external domain. A mesh doing transparent mTLS is not enough: the URL stays `http://`. |
| Railway (not a template target; where `dayuse-agent-fleet` runs) | `http://<svc>.railway.internal:<port>` | **yes** | Either TLS served by the container on the private network (`uvicorn --ssl-keyfile --ssl-certfile`, certificate from an internal CA with `<svc>.railway.internal` in its SAN; callers trust it through a `SSL_CERT_FILE` bundle = public roots + internal CA). Or a Railway public domain (automatic SSL certificates) as `AGENT_PUBLIC_URL` — the leaf becomes reachable from the internet, so inbound auth (`verify_inbound`) is not optional. |

- Railway's docs advise `http://` on the private network because Wireguard already encrypts it. That advice does not survive ADK ≥ 2.7 for agents: the scheme is what ADK checks.
- Container TLS fits the default identity (`oidc-mtls` needs certificates anyway: `agent-identity`). Certificate issuance and rotation on Railway, and the latency/egress cost of the public-domain option: **to collect**.

Sources: https://docs.cloud.google.com/run/docs/triggering/https-request · https://knative.dev/docs/serving/encryption/cluster-local-domain-tls/ · https://docs.railway.com/networking/private-networking/how-it-works · https://docs.railway.com/networking/public-networking · https://github.com/google/adk-python/issues/7139

## Deployment checklist

1. Same image as the other targets (`${DAYUSE_REGISTRY}/agents/<name>:<tag>`).
2. The container listens on `$PORT`, non-root, with no cloud metadata server.
3. Model provider via LiteLLM (`DAYUSE_MODEL`).
4. Secrets via the target's manager, EU region.
5. No essential GCP dependency; `gcp-agent-identity` absent from the image.
6. `AGENT_PUBLIC_URL` and every `*_CARD_URL` are https outside loopback, with the card's `url` on the same origin as the card URL.
