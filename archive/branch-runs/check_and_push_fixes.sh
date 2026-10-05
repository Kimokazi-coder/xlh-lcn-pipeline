#!/usr/bin/env bash
# Checks before every push of publication-fixes, then the push with retries.
#   1. python src/diagnostics.py reference-check must PASS
#   2. python src/diagnostics.py regression must PASS (once the subcommand exists)
#   3. git status on results/ must be clean
# Usage (from the repo root): bash experiments/check_and_push_fixes.sh
# Exit codes: 0 pushed, 2 a check failed (nothing pushed), 3 push failed.
set -u
cd "$(dirname "$0")/.."

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "publication-fixes" ]; then
  echo "not on publication-fixes (on $branch); nothing pushed"
  exit 2
fi

res=$(git status --porcelain -- results/)
if [ -n "$res" ]; then
  echo "CHECK FAILED: results/ is not clean"
  echo "$res" | head
  exit 2
fi
echo "check: results/ is clean"

ref_out=$(python src/diagnostics.py reference-check 2>&1)
echo "$ref_out" | tail -n 2
if ! echo "$ref_out" | grep -q "^PASS: 3 of 3"; then
  echo "CHECK FAILED: reference-check did not pass"
  exit 2
fi

if python src/diagnostics.py regression -h > /dev/null 2>&1; then
  reg_out=$(python -u src/diagnostics.py regression 2>&1)
  echo "$reg_out" | tail -n 3
  if ! echo "$reg_out" | grep -q "^PASS: regression"; then
    echo "CHECK FAILED: regression did not pass"
    exit 2
  fi
else
  echo "check: regression subcommand not present yet, skipped"
fi

res=$(git status --porcelain -- results/)
if [ -n "$res" ]; then
  echo "CHECK FAILED: results/ changed during the checks"
  exit 2
fi

for attempt in 1 2 3 4; do
  if git push origin publication-fixes; then
    echo "pushed on attempt $attempt"
    exit 0
  fi
  if [ "$attempt" -lt 4 ]; then
    echo "push failed, retrying in 30 s"
    sleep 30
  fi
done
echo "PUSH FAILED after retries"
exit 3
