#!/usr/bin/env bash
# Finish the grid-aware structured-rules LLM arm (frozen 40-case subset, three wordings).
# Resumes into experiments/evaluation/test_set_v1/results_school_grid_llm/raw with its own spend
# ledger. A level is done only when all 40 subset cases are recorded; any refusal (503/429) or
# crash waits and retries. Stops cleanly if the ledger cap is reached. Safe to stop and restart.
set -u
cd "$(dirname "$0")/.."
OUT=experiments/evaluation/test_set_v1/results_school_grid_llm
PACE="${PACE:-4}"
MAX_USD="${MAX_USD:-3.00}"
WAIT_ON_REFUSAL="${WAIT_ON_REFUSAL:-120}"
recorded() {
  [ -f "$1" ] || { echo 0; return; }
  py -c "import json,sys; ids=set(json.load(open('experiments/evaluation/test_set_v1/subset_40.json'))['case_ids']); print(len({json.loads(l)['case_id'] for l in open(sys.argv[1],encoding='utf-8') if l.strip()} & ids))" "$1"
}
for level in low medium high; do
  file="$OUT/raw/structured_rules_llm__${level}.jsonl"
  while [ "$(recorded "$file")" -lt 40 ]; do
    out=$(py scripts/run_test_set_v1.py --arm structured_rules_llm --level "$level" --split subset40 \
          --pace-seconds "$PACE" --max-usd "$MAX_USD" --output-dir "$OUT/raw" \
          --spend-ledger "$OUT/spend_ledger.json" 2>&1)
    if echo "$out" | grep -q "BUDGET:"; then
      echo "$(date '+%Y-%m-%d %H:%M') $(echo "$out" | grep BUDGET | cut -c1-160) -- stopping"
      exit 3
    fi
    summary=$(echo "$out" | grep -E "wrote|Stopped" | cut -c1-160)
    [ -z "$summary" ] && summary="CRASH: $(echo "$out" | grep -v -i warn | tail -3 | tr '\n' ' ' | cut -c1-300)"
    echo "$(date '+%Y-%m-%d %H:%M') $level $summary"
    [ "$(recorded "$file")" -lt 40 ] && sleep "$WAIT_ON_REFUSAL"
  done
done
echo "$(date '+%Y-%m-%d %H:%M') grid-aware structured-rules arm complete"
