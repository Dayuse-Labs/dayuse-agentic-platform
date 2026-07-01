#!/usr/bin/env bash
# Dayuse static guardrail — fails if the code introduces a forbidden dependency.
# Copy into the generated agent's scripts/, then run in CI + locally.
set -euo pipefail
root="${1:-.}"
fail=0

# 1) gcp_agent_identity imported outside the get_identity_provider factory
if grep -rn --include='*.py' 'gcp_agent_identity' "$root" \
   | grep -v 'provider.py' | grep -v 'gcp_agent_identity.py'; then
  echo "ERROR: hard GCP dependency detected (gcp_agent_identity outside factory)."; fail=1
fi

# 2) cloud model SDK imported hardcoded instead of LiteLLM
if grep -rn --include='*.py' -E 'import vertexai|from vertexai|import boto3.*bedrock' "$root"; then
  echo "ERROR: hardcoded cloud model SDK — use LiteLLM instead."; fail=1
fi

# 3) the code must use LiteLlm
if ! grep -rqn --include='*.py' 'LiteLlm' "$root"; then
  echo "WARNING: no LiteLlm usage found — check the model provider."
fi

[ "$fail" -eq 0 ] && echo "Dayuse guardrails: OK"
exit "$fail"
