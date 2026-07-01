# Leaf-agent registry & reuse

The "deploy once, reuse everywhere" principle relies on a **registry** of deployed A2A leaves. Before scaffolding a leaf, the orchestrator looks it up here.

## Registry convention

A versioned `agents-registry.yaml` file (at the root of the agentic platform repo, on GitLab) lists the deployed leaves. **A seed template is shipped** at `${CLAUDE_PLUGIN_ROOT}/skills/scaffold-orchestrator/templates/agents-registry.yaml.tmpl` — on day one (no registry yet), copy it to the repo root and keep the empty `agents:` list; entries are added as leaves get exposed. Schema:

```yaml
# agents-registry.yaml — deployed A2A leaves, shared across orchestrators.
agents:
  - name: spec_generator
    description: Turns a signal (logs, ticket) into a spec.
    card_url: https://agents.dayuse.io/spec-generator/.well-known/agent-card.json
    env: SPEC_GENERATOR_CARD_URL
    owner: team-platform
    writes: false
  - name: coder
    description: Applies a fix according to a spec.
    card_url: https://agents.dayuse.io/coder/.well-known/agent-card.json
    env: CODER_CARD_URL
    writes: false
  - name: tester
    description: Writes/runs the tests and reports.
    card_url: https://agents.dayuse.io/tester/.well-known/agent-card.json
    env: TESTER_CARD_URL
    writes: false
  - name: mr_writer
    description: Writes and pushes a GitLab Merge Request.
    card_url: https://agents.dayuse.io/mr-writer/.well-known/agent-card.json
    env: MR_WRITER_CARD_URL
    writes: true        # => mandatory HITL point
```

## Search for an existing leaf

1. Read `agents-registry.yaml` and look for an entry whose `description`/`name` covers the wanted capability.
2. In addition, via the **GitLab** MCP, search for an existing agent repo (naming convention `agent-<name>`), to spot a leaf not yet registered.
3. If found → reuse: declare a `RemoteA2aAgent(agent_card=os.environ["<ENV>"])` and add the env variable (`<ENV>=<card_url>`) to the orchestrator's `.env.example`.

## Register a new leaf

When a new leaf is exposed (handled by `wire-a2a` Step 7):

1. Add an entry to `agents-registry.yaml` (name, description, card_url, env, owner, `writes`).
2. The commit for this update goes through **HITL** (GitLab write).
3. Subsequent orchestrators will see it and reuse it.

## Rules

- Never duplicate a capability already present in the registry: reuse.
- Any leaf with `writes: true` requires a HITL point at the orchestrator that calls it.
- The card URL is resolved via an environment variable (never a hard-coded URL in the code).
