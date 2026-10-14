# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An internal **Claude Code plugin** (`dayuse-agentic-platform`) that encodes Dayuse's conventions for building portable ADK Python agents. It is knowledge, not runtime: skills, two review subagents, one PreToolUse hook, and two bundled documentation MCPs. The agents themselves live in the sibling `dayuse-agent-fleet` repo; business MCP servers (GitLab, MySQL, Sentry…) are wired into generated agents, never into this plugin.

The repo doubles as its own marketplace source: `.claude-plugin/marketplace.json` lists the plugin with `"source": "./"`. Version bumps must touch both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Commands / validation

There is no build, lint, or test suite. Almost everything is markdown + JSON; validate changes by reading them. The only executable is the static guardrail script (canonical copy here, copied into generated agents and run in the fleet's CI):

```bash
bash skills/eval-agent/scripts/dayuse_guardrails.sh <agent_path>   # exit 0 = OK
```

After editing `hooks/hooks.json`, `.mcp.json`, or the `.claude-plugin/*.json` manifests, check they are still valid JSON (`jq . <file>`). To exercise the plugin end-to-end, install it into a session from the local marketplace (`/plugin marketplace add <path-to-this-repo>`).

## Architecture

### Delegation principle (the core design rule)

This plugin sits **on top of** the Google `google-agents-cli-*` skills and must never duplicate generic ADK knowledge (scaffolding, patterns, eval harness, standard deployment). Skills here delegate that and add only the Dayuse overlay: LiteLLM-only model access, portable containers, pluggable identity, A2A conventions, GDPR/HITL guardrails. When editing a skill, if content is generic ADK, the fix is a pointer to `agents-cli` (or the bundled `adk-docs` MCP), not a rewrite here.

### Skill anatomy

Each skill under `skills/<name>/` follows progressive disclosure:

- **`SKILL.md`** — frontmatter `description` is the trigger surface (it lists the literal phrases that auto-load the skill — preserve them when editing) + a stepwise body.
- **`references/*.md`** — detail loaded on demand (checklists, code skeletons, trade-offs).
- **`templates/*.tmpl`** — files to copy into generated agents with `{{PLACEHOLDER}}` substitution; placeholders are documented in `skills/scaffold-agent/references/dayuse-defaults.md`.
- Skills reference their own files via `${CLAUDE_PLUGIN_ROOT}/skills/...` paths.

Four knowledge skills (`agent-architecture`, `agent-identity`, `gdpr-guardrails`, `decision-models`) set the mental model; five action skills (`scaffold-agent`, `scaffold-orchestrator`, `wire-a2a`, `deploy-anywhere`, `eval-agent`) build on it. `agent-architecture` is the root: every other skill assumes its vocabulary (leaf vs orchestrator, A2A = agent↔agent / MCP = agent↔tool, 4-layer portability stack, sharing criteria).

### Cross-file source-of-truth graph

Content is deliberately single-sourced and *copied by reference* across skills — edits must keep the graph coherent:

- `AgentIdentityProvider` skeleton lives in `skills/agent-identity/references/identity-providers.md`; `scaffold-agent` Step 4 copies it into generated agents.
- `TokenBroker` lives in `skills/gdpr-guardrails/references/data-residency.md`; `scaffold-agent` copies it too.
- The zero-lock-in checklist lives in `skills/agent-architecture/references/portability-stack.md`; `scaffold-agent` Step 6 and the `portability-compliance-auditor` agent both check against it.
- `dayuse_guardrails.sh` lives in `skills/eval-agent/scripts/`; the auditor agent runs it, and the fleet's CI runs the copied version.
- `decision_eval.py` lives in `skills/eval-agent/scripts/` too; `eval-agent` Step 4, `decision-models` Step 6 and the auditor's decision-point check all point to it.
- Decision models: the "route, never approve" rule lives in `skills/gdpr-guardrails/SKILL.md` §4; the pinned-version + safe-branch item is #6 of the checklist in `portability-stack.md`; `skills/decision-models/` points to both and owns `templates/decision.py.tmpl`.

The two subagents are a before/after pair: `agents/agent-design-reviewer.md` reviews a *design* before scaffolding (read-only, no Bash); `agents/portability-compliance-auditor.md` audits *generated code* after (runs the guardrail script, then reasons over what the script cannot see).

### Invariants the plugin encodes (non-negotiable)

Model access via LiteLLM only (`DAYUSE_MODEL`), zero GCP lock-in (one OCI image → Cloud Run + k8s/Knative; GCP is a test target), A2A for orchestrator↔leaf and MCP for agent↔tool, pluggable identity behind `AgentIdentityProvider` (`gcp-agent-identity` never imported outside the factory), HITL on every external write, EU data residency with a token broker. Any skill/template/agent edit that weakens one of these is wrong by definition — see README "Architecture decisions".

## Gotchas

- **The HITL hook matcher** in `hooks/hooks.json` must only match `mcp__gitlab__…`/`mcp__notion__…` *write* tool names. If it ever matches `Write|Edit` (or greedily matches everything), it blocks all local file writes for every plugin user. It intentionally matches by tool-name pattern so it works with whatever GitLab MCP the user has connected — the plugin deliberately embeds no GitLab server.
- The `adk-docs` MCP in `.mcp.json` is stdio via `uvx` and requires `uv` on the machine; `context7` (HTTP, `CONTEXT7_API_KEY`) is the fallback. Don't make skills hard-depend on `adk-docs` being up.
- Template defaults (model name in `dayuse-defaults.md`, ports, env var names) are mirrored in the fleet's real `.env` conventions — changing a default here without checking `dayuse-agent-fleet` desynchronizes the conventions from their only executable proof.
