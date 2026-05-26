#!/usr/bin/env bash
# End-to-end FoodShield demo against a live API.
#
# Prereqs:
#   make up    # docker compose -f infra/docker-compose.yml up -d
#   # ...wait for healthchecks: make ps
#
# This script POSTs the same 3-region Horn-of-Africa scenario through every
# endpoint and pipes responses through jq.

set -euo pipefail
API="${API_URL:-http://localhost:8000}"

if ! command -v jq >/dev/null; then
    echo "jq is required for pretty-printing. brew install jq / apt install jq" >&2
    exit 1
fi

SCENARIO='{
  "101": {"drought": 0.90, "heat": 0.75},
  "102": {"drought": 0.92, "heat": 0.72},
  "201": {"drought": 0.70, "heat": 0.55, "pest": 0.30}
}'

hr() { printf '\n\033[1m%s\033[0m\n' "── $1 ─────────────────────────────────────────────"; }

hr "1) /health"
curl -fsS "$API/health" | jq .

hr "2) /simulate"
curl -fsS -X POST "$API/simulate" \
  -H 'Content-Type: application/json' \
  -d "{\"scenario\": $SCENARIO}" | jq .

hr "3) /project (3/6/12 mo)"
curl -fsS -X POST "$API/project" \
  -H 'Content-Type: application/json' \
  -d "{\"scenario\": $SCENARIO, \"horizons_months\": [3, 6, 12]}" | jq .

hr "4) /recommend (10kt, \$5M, prioritize SOM, avoid conflict)"
REC_BODY=$(jq -n --argjson s "$SCENARIO" '{
  scenario: $s,
  total_tonnage: 10000,
  total_budget_usd: 5000000,
  priority_population_groups: ["SOM"],
  avoid_conflict_zones: true
}')
curl -fsS -X POST "$API/recommend" \
  -H 'Content-Type: application/json' \
  -d "$REC_BODY" | jq .

hr "5) /export/policy → policy.csv"
curl -fsS -X POST "$API/export/policy" \
  -H 'Content-Type: application/json' \
  -d "$REC_BODY" -o policy.csv
echo "wrote $(wc -l < policy.csv) lines to policy.csv"
head -5 policy.csv
