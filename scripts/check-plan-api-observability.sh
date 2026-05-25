#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3010}"

pretty_json() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool
  else
    cat
  fi
}

show_get() {
  local path="$1"
  printf '\n== GET %s ==\n' "${path}"
  curl -fsS "${BASE_URL}${path}" | pretty_json
}

plan_payload="$(mktemp)"
trap 'rm -f "${plan_payload}"' EXIT

cat >"${plan_payload}" <<'JSON'
{
  "trail_id": "vermont_long_trail",
  "direction": "NOBO",
  "ingress_route": "North Adams Approach",
  "egress_route": "Journey's End Trail",
  "desired_days": 28,
  "min_daily_miles": 8,
  "max_daily_miles": 14,
  "max_daily_elevation": 4500,
  "resupply_cadence": 5,
  "recovery_cadence": 5,
  "planned_start_date": "2026-07-15"
}
JSON

show_get "/health"
show_get "/ready"
show_get "/version"
show_get "/metrics"

printf '\n== POST /plan ==\n'
curl -fsS \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@${plan_payload}" \
  "${BASE_URL}/plan" \
  | python3 -c 'import json, sys; data=json.load(sys.stdin); first=data["daily_plan"][0]; summary={"export_version": data["export_version"], "build_sha": data["build_sha"], "trail_id": data["trail_id"], "daily_plan_count": len(data["daily_plan"]), "first_day": "{} -> {}".format(first["daily_start_location"], first["daily_stop_location"])}; print(json.dumps(summary, indent=2))'

show_get "/metrics"
