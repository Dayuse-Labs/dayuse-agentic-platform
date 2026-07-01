# Orchestrator ↔ leaf agents patterns

An orchestrator composes A2A leaf agents. Choose the pattern according to the shape of the work. All are implemented in ADK; delegate the ADK skeleton to `agents-cli`, adding only the A2A composition and the Dayuse defaults.

## Inventory of typical leaf agents at Dayuse

| Leaf | Role | Wired MCP tools |
|---|---|---|
| `coder` | applies a fix / writes code from a spec | GitLab (read), filesystem |
| `tester` | writes/runs the tests, reports | GitLab, CI runner |
| `mr-writer` | writes and pushes a Merge Request | GitLab (write, **HITL**) |
| `spec-generator` | turns a signal (logs, ticket) into a spec | logs, Notion (read) |
| `spec-evaluator` | scores/critiques a spec, improvement loop | — |

Each leaf is deployed **once** and reused by several orchestrators.

## Pattern 1 — Sequential (pipeline)

The most common one. "logs → spec → fix → MR" flow:

1. `spec-generator` ← signal (extracted from Sentry/Elasticsearch logs).
2. `spec-evaluator` scores the spec; loops until threshold (pattern 4).
3. `coder` applies the fix.
4. `tester` validates.
5. `mr-writer` pushes the MR → **mandatory HITL** before push.

"Notion ticket → spec → fix → MR" flow: identical, but the input to `spec-generator` is a Notion ticket instead of logs. **Leaves 2→5 are the same** — this is the whole point of sharing.

## Pattern 2 — Parallel (fan-out / fan-in)

Launch several leaves in parallel then aggregate (e.g. `tester` + `spec-evaluator` analysis at the same time). Use an ADK parallel agent; each branch is an independent A2A call.

## Pattern 3 — Routing (dispatch)

The orchestrator classifies the intent then routes to the right leaf (e.g. "bug" → fix flow; "doc" → writing flow). The router is an `LlmAgent` that chooses the target `AgentTool`/`RemoteA2aAgent`.

## Pattern 4 — spec ↔ eval loop

`spec-generator` produces, `spec-evaluator` scores, and we iterate as long as the score < threshold or `max_iterations` is not reached. Always bound the iterations to avoid infinite loops and keep cost under control.

## Composition rules

- The orchestrator **never reimplements** a leaf's logic; it calls it over A2A.
- Every final write operation (MR, issue, Notion) goes through a dedicated leaf and triggers the **HITL**.
- The orchestrator is itself containerized and portable (same 4 layers).
- Bound the loops and the call depths; log every A2A hop for traceability.
