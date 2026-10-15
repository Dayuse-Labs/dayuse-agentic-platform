# A2A Agent Card — schema & signing (Dayuse conventions)

The Agent Card is the public contract of an A2A leaf, published on `/.well-known/agent-card.json`. Confirm the exact fields against the installed A2A/ADK version (via `agents-cli` / Context7); below is the stable structure and our conventions.

## Fields

| Field | Role |
|---|---|
| `name`, `description`, `version` | functional identity of the agent |
| `url` | A2A endpoint (from `AGENT_PUBLIC_URL`, never hard-coded); `https` off loopback, same origin as the card URL (see § Transport) |
| `provider` | `{ "organization": "Dayuse", "url": "https://dayuse.com" }` |
| `capabilities` | e.g. `{ "streaming": true }` |
| `defaultInputModes` / `defaultOutputModes` | e.g. `["text/plain"]` |
| `skills[]` | `{ id, name, description, tags, examples?, inputModes?, outputModes? }` |
| `securitySchemes` | auth schemes (OpenAPI 3 style) |
| `security` | which schemes are required |
| `signatures` | JWS signature(s) of the card |

## Transport — https off loopback (ADK ≥ 2.7)

`RemoteA2aAgent` checks where a card fetched over the network may send traffic. Read in the `google-adk` wheels published on PyPI: 2.6.3 has neither check, 2.12.0 has both, unchanged.

| Since | What is checked | Error (`AgentCardResolutionError`) |
|---|---|---|
| 2.7.0 | Every RPC URL the card offers is `https` (or `http` on a loopback host) **and** shares the origin (scheme, host, port) of the URL the card was fetched from. | `Agent card RPC URL must use https, or http on a loopback host: <url>` |
| 2.9.0 | The card URL itself, before the request: the card request interceptors attach the invocation's credential, so a plain-http fetch would send it in clear. | `Agent card URL must use https, or http on a loopback host: <url>` |

- Loopback means `localhost`, `*.localhost` and loopback IP literals. It is the only case where plain `http` passes: local development.
- In practice an `http` card URL off loopback fails from 2.7.0 already: either the card's `url` is `http` (refused) or it is `https`, hence another origin (refused).
- No flag, config field or env var turns the checks off in 2.12.0. An opt-in (`allow_insecure_http`) is proposed in google/adk-python#7139 (PR #7169), not merged. Whether and when it lands: **to collect**.
- Transparent mTLS from a service mesh (sidecars) does not satisfy the check: the URL the agent sees is still `http://` (#7139).
- A card passed as an `AgentCard` object, or read from a local file, is not checked. That is a bypass, not a Dayuse pattern: it drops live card discovery and skips the check on purpose.

**Dayuse rule.** Every card URL an orchestrator reads, and every `url` a card advertises, is `https` outside loopback, and `AGENT_PUBLIC_URL` is the exact origin callers fetch the card from. TLS can end at the platform (Cloud Run, a public domain, an ingress) or in the container (`uvicorn --ssl-keyfile … --ssl-certfile …`, plus `--ssl-ca-certs` and `--ssl-cert-reqs` to require client certificates for mTLS). Only `RemoteA2aAgent` enforces this; an A2A call made with raw httpx is not blocked by ADK but falls under the same rule. Per target: `deploy-anywhere/references/targets.md` § A2A transport.

**Internal CA.** When a leaf's certificate comes from an internal CA, the caller must trust it. httpx, which the A2A client uses, reads `SSL_CERT_FILE` when it builds its default TLS context, and that file **replaces** the default trust store. Point it at a bundle holding the public roots **plus** the internal CA; with the internal CA alone, calls to public https endpoints (the model provider) can start failing.

Sources: `google-adk` 2.6.3, 2.7.0, 2.9.0 and 2.12.0 wheels (`remote_a2a_agent.py`, moved to `a2a/agent/_remote_a2a_agent.py` in 2.12); https://github.com/google/adk-python/issues/7139; Spike A (`dayuse-agent-fleet`, 2026-10-14): `http://log-analyzer.railway.internal:8080/...` refused by 2.12.0 before any network call; httpx 0.28.1 `_config.py`; https://www.uvicorn.dev/settings.

## `securitySchemes` by provider

`oidc-mtls` (default):

```json
"securitySchemes": {
  "dayuse-oidc": {
    "type": "openIdConnect",
    "openIdConnectUrl": "${DAYUSE_OIDC_ISSUER}/.well-known/openid-configuration"
  },
  "mtls": { "type": "mutualTLS" }
},
"security": [ { "dayuse-oidc": [], "mtls": [] } ]
```

`spire` :

```json
"securitySchemes": {
  "mtls": { "type": "mutualTLS" },
  "spiffe-jwt": { "type": "http", "scheme": "bearer", "bearerFormat": "JWT-SVID" }
},
"security": [ { "mtls": [] } ]
```

## Signing (JWS / JCS)

1. Build the card without the `signatures` field.
2. Canonicalize the JSON via **JCS** (RFC 8785).
3. Sign with **JWS** (RFC 7515) using the agent's key → call `identity.sign_agent_card(card)`.
4. Add the result into `signatures` and publish.

Consumer side: `identity.verify_agent_card(card)` recanonicalizes and verifies the signature before any call. A card whose signature is invalid is **rejected**.

## Checks

- `GET /.well-known/agent-card.json` returns a valid and signed card.
- Off loopback, the card URL and every `url` in the card are `https` and share one origin.
- The declared `securitySchemes` are actually required by the server (`verify_inbound`).
- A `RemoteA2aAgent(agent_card="<url>")` resolves, verifies the signature, and calls the agent.
