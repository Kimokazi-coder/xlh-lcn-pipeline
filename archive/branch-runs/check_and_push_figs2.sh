#!/usr/bin/env bash
# Checks before every push of figures-v2, then the push with retries.
#   1. git status on results/ must be clean
#   2. src/, config.py and requirements.txt must equal the base SHA
#   3. python src/diagnostics.py reference-check must PASS
#   4. with -g: python src/diagnostics.py regression must PASS (final push)
# Usage (from the repo root): bash experiments/check_and_push_figs2.sh [-g]
# Exit codes: 0 pushed, 2 a check failed (nothing pushed), 3 push failed.
set -u
cd "$(dirname "$0")/.."
BASE=867338079ce8a9c97cd69c1551ca42e68fb1bebb

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "figures-v2" ]; then
  echo "not on figures-v2 (on $branch); nothing pushed"
  exit 2
fi

res=$(git status --porcelain -- results/)
if [ -n "$res" ]; then
  echo "CHECK FAILED: results/ is not clean"
  echo "$res" | head
  exit 2
fi
echo "check: results/ is clean"

diff_out=$(git diff "$BASE" -- src config.py requirements.txt)
if [ -n "$diff_out" ]; then
  echo "CHECK FAILED: src/, config.py or requirements.txt differ from the base"
  exit 2
fi
echo "check: src/, config.py, requirements.txt equal the base"

ref_out=$(python src/diagnostics.py reference-check 2>&1)
echo "$ref_out" | tail -n 2
if ! echo "$ref_out" | grep -q "^PASS: 3 of 3"; then
  echo "CHECK FAILED: reference-check did not pass"
  exit 2
fi

if [ "${1:-}" = "-g" ]; then
  reg_out=$(python -u src/diagnostics.py regression 2>&1)
  echo "$reg_out" | tail -n 3
  if ! echo "$reg_out" | grep -q "^PASS: regression"; then
    echo "CHECK FAILED: regression did not pass"
    exit 2
  fi
fi

res=$(git status --porcelain -- results/)
if [ -n "$res" ]; then
  echo "CHECK FAILED: results/ changed during the checks"
  exit 2
fi

for attempt in 1 2 3 4; do
  if git push origin figures-v2; then
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
