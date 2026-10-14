#!/usr/bin/env bash
# Dayuse static guardrail — fails if the code introduces a forbidden dependency.
# Canonical copy: dayuse-agentic-platform/skills/eval-agent/scripts/. Copied into generated agents'
# scripts/ and into dayuse-agent-fleet/scripts/. Run in CI + locally.
set -euo pipefail
root="${1:-.}"
fail=0

# Vendored code is not our code. A local dev venv (`.venv-run`, built by run_local.sh) ships
# litellm's own `import vertexai` lines, so every local run failed on a false positive that had
# to be remembered and ignored — and a wall of noise is exactly where a real hit gets missed.
# CI has no venv, so this never affected the CI verdict, only the local signal.
skip=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=.venv-run --exclude-dir=venv
      --exclude-dir=site-packages --exclude-dir=node_modules --exclude-dir=__pycache__)

# 1) gcp_agent_identity imported outside the get_identity_provider factory
if grep -rn "${skip[@]}" --include='*.py' 'gcp_agent_identity' "$root" \
   | grep -v 'provider.py' | grep -v 'gcp_agent_identity.py'; then
  echo "ERROR: hard GCP dependency detected (gcp_agent_identity outside factory)."; fail=1
fi

# 2) cloud model SDK imported hardcoded instead of LiteLLM
if grep -rn "${skip[@]}" --include='*.py' -E 'import vertexai|from vertexai|import boto3.*bedrock' "$root"; then
  echo "ERROR: hardcoded cloud model SDK — use LiteLLM instead."; fail=1
fi

# 4) HITL: the unattended-write exemption (R2) must not spread beyond the leaf it was granted to.
# There is exactly ONE agent allowed to write without asking a human — agents/mr_commenter, MR
# review comments — and the decision lives in a private class there on purpose. Two checks:
#   a) the auto-approver's name must not appear anywhere else;
#   b) any OTHER agent that calls commit_write must also name GoogleChatApprover, i.e. it must be
#      asking a human. A new write leaf that quietly supplies its own always-yes approver fails here.
if grep -rn "${skip[@]}" --include='*.py' '_UnattendedApprover' "$root"    | grep -v 'agents/mr_commenter/'; then
  echo "ERROR: the unattended-write approver (R2) is only for agents/mr_commenter — every other write must go through a human approver."; fail=1
fi
for agent_dir in "$root"/agents/*/; do
  case "$agent_dir" in *"/mr_commenter/"*) continue ;; esac
  if grep -rqn "${skip[@]}" --include='*.py' 'commit_write(' "$agent_dir"      && ! grep -rqn "${skip[@]}" --include='*.py' 'GoogleChatApprover' "$agent_dir"; then
    echo "ERROR: $(basename "$agent_dir") calls commit_write without GoogleChatApprover — HITL is the default (invariant 5); only R2 (mr_commenter) is exempt."; fail=1
  fi
done

# 5) the review pair must never acquire a code-write path (§6.13, 2026-09-04).
# The whole argument for posting MR review comments and ```suggestion blocks unattended (exemption
# R2) is that neither agent CAN write code: a suggestion is not code until a developer clicks Apply,
# and GitLab attributes that commit to the developer. That argument survives only while the code
# path is absent — so the absence is checked, not asserted in a docstring. A `git push`, a
# `repository/commits` POST or a `subprocess` call appearing in either agent package would silently
# turn a reviewer into a committer.
# Scoped to the agent PACKAGES: agents/mr_review/scripts/calibrate.py legitimately shells out to
# `git show` to replay historical diffs, and it is a dev harness that never runs in a deployment.
for pkg in "$root"/agents/mr_review/mr_review "$root"/agents/mr_commenter/mr_commenter; do
  [ -d "$pkg" ] || continue
  if grep -rn "${skip[@]}" --include='*.py' -E 'repository/commits|repository/branches|subprocess|[^a-z_]push\(' "$pkg"; then
    echo "ERROR: $(basename "$(dirname "$pkg")") must have NO commit/branch/push/subprocess path — that is what makes HITL exemption R2 defensible (plan §6.13)."; fail=1
  fi
done

# 6) Decision models go through LiteLLM like every other model (decision-models skill, rule 1).
# A vendor SDK or a raw HTTP call to a decision endpoint bypasses the gateway — no cost tracking, no
# fallback — and turns the provider into a code dependency instead of an env variable.
if grep -rn "${skip[@]}" --include='*.py' -E \
     '^[[:space:]]*(import|from)[[:space:]]+typesafe|api\.typesafe\.ai|https?://[^"'"'"' ]*/(v1|api/alpha)/(systemone|decisions)|\.decisions\.create\(' "$root" \
   || grep -rn "${skip[@]}" --include='requirements*.txt' --include='pyproject.toml' -E '^[[:space:]"]*typesafe-sdk' "$root"; then
  echo "ERROR: decision model called outside LiteLLM (vendor SDK or raw /v1/systemone, /v1/decisions, OpenRouter /api/alpha/decisions) — use litellm.asystemone / litellm.adecisions."; fail=1
fi

# 7) Decision models are pinned. An alias moves when the vendor ships, and thresholds tuned on one
# version silently stop holding on the next (decision-models, rule 2). `.env` itself is skipped:
# CI never has it, and grep would print its lines.
if grep -rn "${skip[@]}" --exclude='.env' \
     --include='*.py' --include='*.example' --include='*.yaml' --include='*.yml' --include='*.toml' --include='*.json' \
     -E 'jev-(latest|preview)|DAYUSE_DECISION_MODEL[[:space:]]*[=:][[:space:]]*["'"'"']?[^[:space:]"'"'"'#]*-(latest|preview)|DAYUSE_DECISION_MODEL"[[:space:]]*,[[:space:]]*"[^"]*-(latest|preview)"' "$root"; then
  echo "ERROR: unpinned decision model — set DAYUSE_DECISION_MODEL to an exact version (e.g. openrouter/typesafe/jev-1.13.0)."; fail=1
fi

# 8) A decision never approves a write (gdpr-guardrails §4). Static form of the rule: a module that
# asks a decision model does not also perform the external write. It routes or escalates; the write
# lives in its write leaf, behind its own HITL checkpoint. Tests are skipped: they may stub both.
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in */tests/*|*/test_*.py) continue ;; esac
  if grep -qn 'commit_write(' "$f"; then
    echo "ERROR: $f asks a decision model and calls commit_write — a decision can route or escalate, never approve a write (gdpr-guardrails §4)."; fail=1
  fi
done < <(grep -rlE "${skip[@]}" --include='*.py' 'asystemone|adecisions|litellm\.(systemone|decisions)|decide_(choice|noul)\(' "$root" || true)

# 3) the code must use LiteLlm
if ! grep -rqn "${skip[@]}" --include='*.py' 'LiteLlm' "$root"; then
  echo "WARNING: no LiteLlm usage found — check the model provider."
fi

[ "$fail" -eq 0 ] && echo "Dayuse guardrails: OK"
exit "$fail"
