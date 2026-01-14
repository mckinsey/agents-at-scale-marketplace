#!/usr/bin/env bash
set -euo pipefail

# Debug: log that hook was invoked
echo "[DEBUG] protect-git-push hook invoked at $(date)" >> /tmp/git-push-hook.log

# Read the command from stdin
input=$(cat)
echo "[DEBUG] Input: $input" >> /tmp/git-push-hook.log
cmd=$(echo "$input" | jq -r '.tool_input.command // ""')
echo "[DEBUG] Command: $cmd" >> /tmp/git-push-hook.log

# Only process git push commands
if ! echo "$cmd" | grep -Eq '^\s*git\s+push'; then
  exit 0
fi

# Block pushes directly to main or master
if echo "$cmd" | grep -Eq 'git\s+push\s+(origin\s+)?(main|master)\b'; then
  echo "BLOCKED: Direct push to main/master is not allowed. Create a PR instead." >&2
  exit 2
fi

# Block force pushes to main/master
if echo "$cmd" | grep -Eq 'git\s+push.*--force.*\s+(main|master)\b|git\s+push.*\s+(main|master)\b.*--force'; then
  echo "BLOCKED: Force push to main/master is not allowed." >&2
  exit 2
fi

# For all other git push commands, require user approval
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Git push requires explicit approval"
  }
}
EOF

exit 0
