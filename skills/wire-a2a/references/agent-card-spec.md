# A2A Agent Card — schema & signing (Dayuse conventions)

The Agent Card is the public contract of an A2A leaf, published on `/.well-known/agent-card.json`. Confirm the exact fields against the installed A2A/ADK version (via `agents-cli` / Context7); below is the stable structure and our conventions.

## Fields

| Field | Role |
|---|---|
| `name`, `description`, `version` | functional identity of the agent |
| `url` | A2A endpoint (from `AGENT_PUBLIC_URL`, never hard-coded) |
| `provider` | `{ "organization": "Dayuse", "url": "https://dayuse.com" }` |
| `capabilities` | e.g. `{ "streaming": true }` |
| `defaultInputModes` / `defaultOutputModes` | e.g. `["text/plain"]` |
| `skills[]` | `{ id, name, description, tags, examples?, inputModes?, outputModes? }` |
| `securitySchemes` | auth schemes (OpenAPI 3 style) |
| `security` | which schemes are required |
| `signatures` | JWS signature(s) of the card |

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
- The declared `securitySchemes` are actually required by the server (`verify_inbound`).
- A `RemoteA2aAgent(agent_card="<url>")` resolves, verifies the signature, and calls the agent.
