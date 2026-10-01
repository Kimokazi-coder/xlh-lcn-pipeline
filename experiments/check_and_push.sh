#!/usr/bin/env bash
# Rule 2 checks, then push overnight-fixes with up to 3 retries.
# Usage (from the repo root): bash experiments/check_and_push.sh
# Exit codes: 0 pushed, 2 a check failed (nothing pushed), 3 push failed.
set -u
cd "$(dirname "$0")/.."

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "overnight-fixes" ]; then
  echo "not on overnight-fixes (on $branch); nothing pushed"
  exit 2
fi

diff_out=$(git diff main -- src config.py)
if [ -n "$diff_out" ]; then
  echo "CHECK FAILED: src/ or config.py differs from main"
  exit 2
fi
echo "check: git diff main src config.py is empty"

ref_out=$(python src/diagnostics.py reference-check 2>&1)
echo "$ref_out" | tail -n 6
if ! echo "$ref_out" | grep -q "^PASS: 3 of 3"; then
  echo "CHECK FAILED: reference-check did not pass"
  exit 2
fi

for attempt in 1 2 3 4; do
  if git push origin overnight-fixes; then
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
