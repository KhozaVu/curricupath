#!/usr/bin/env bash
# Drive both LLM baselines over all three levels until every case is recorded.
# Paced for the Gemini free tier. An arm/level is finished only when its raw file holds all
# 40 subset cases; any other outcome (503 high demand, 429 quota, a crash) waits and resumes from the
# last recorded case. Safe to stop and restart at any time.
set -u
cd "$(dirname "$0")/.."
PACE="${PACE:-1}"
MAX_USD="${MAX_USD:-3.00}"
WAIT_ON_REFUSAL="${WAIT_ON_REFUSAL:-120}"
RAW=experiments/evaluation/test_set_v1/results/raw
TOTAL=40  # frozen 40-case subset (subset_40.json), nested in subset_60.json
# Cases of the frozen subset already recorded in a raw file.
recorded() {
  [ -f "$1" ] || { echo 0; return; }
  py -c "import json,sys; ids=set(json.load(open('experiments/evaluation/test_set_v1/subset_40.json'))['case_ids']); print(len({json.loads(l)['case_id'] for l in open(sys.argv[1],encoding='utf-8') if l.strip()} & ids))" "$1"
}
for level in low medium high; do
  for arm in structured_rules_llm handbook_rag; do
    file="$RAW/${arm}__${level}.jsonl"
    while [ "$(recorded "$file")" -lt "$TOTAL" ]; do
      out=$(py scripts/run_test_set_v1.py --arm "$arm" --level "$level" --split subset40 --pace-seconds "$PACE" --max-usd "$MAX_USD" 2>&1)
      summary=$(echo "$out" | grep -E "wrote|Stopped" | cut -c1-160)
      if echo "$out" | grep -q "BUDGET:"; then
        echo "$(date '+%Y-%m-%d %H:%M') $(echo "$out" | grep BUDGET | cut -c1-160) -- stopping"
        exit 3
      fi
      [ -z "$summary" ] && summary="CRASH: $(echo "$out" | grep -v -i warn | tail -3 | tr '\n' ' ' | cut -c1-300)"
      echo "$(date '+%Y-%m-%d %H:%M') $summary"
      [ "$(recorded "$file")" -lt "$TOTAL" ] && sleep "$WAIT_ON_REFUSAL"
    done
  done
done
echo "$(date '+%Y-%m-%d %H:%M') all LLM arms complete"
