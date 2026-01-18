#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
CONFIG="${CONFIG:-data/scheduler_config.json}"

if [[ "$ACTION" != "run" && "$ACTION" != "schedule" && "$ACTION" != "validate" && "$ACTION" != "info" ]]; then
  echo "Usage: $0 {run|schedule|validate|info}" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to read $(basename "$CONFIG")." >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "Config file not found: $CONFIG" >&2
  exit 1
fi

default_exchange="$(jq -r '.default_exchange // empty' "$CONFIG")"
default_schedule_time="$(jq -r '.scheduler.schedule_time // .schedule_time // empty' "$CONFIG")"

exchange="${EXCHANGE:-$default_exchange}"

if [[ -z "$exchange" || "$exchange" == "null" ]]; then
  echo "Missing EXCHANGE and no default_exchange in config." >&2
  exit 2
fi

mapfile -t allowed_exchanges < <(
  jq -r '.exchanges[]? | if type=="object" then .name else . end' "$CONFIG"
)
if [[ ${#allowed_exchanges[@]} -gt 0 ]]; then
  found_exchange=false
  for ex in "${allowed_exchanges[@]}"; do
    if [[ "$ex" == "$exchange" ]]; then
      found_exchange=true
      break
    fi
  done
  if [[ "$found_exchange" != "true" ]]; then
    echo "Invalid EXCHANGE: $exchange. Allowed: ${allowed_exchanges[*]}" >&2
    exit 2
  fi
fi

mapfile -t allowed_pairs < <(
  jq -r --arg ex "$exchange" \
    '(.exchanges // []) | map(select((type=="object" and .name==$ex) or (type!="object" and .==$ex))) | first | .pairs[]?' \
    "$CONFIG"
)
if [[ ${#allowed_pairs[@]} -eq 0 ]]; then
  mapfile -t allowed_pairs < <(jq -r '.pairs[]?' "$CONFIG")
fi

mapfile -t allowed_timeframes < <(
  jq -r --arg ex "$exchange" \
    '(.exchanges // []) | map(select((type=="object" and .name==$ex) or (type!="object" and .==$ex))) | first | .timeframes[]?' \
    "$CONFIG"
)
if [[ ${#allowed_timeframes[@]} -eq 0 ]]; then
  mapfile -t allowed_timeframes < <(jq -r '.timeframes[]?' "$CONFIG")
fi

split_csv_or_space() {
  local raw="$1"
  raw="${raw//,/ }"
  for item in $raw; do
    if [[ -n "$item" ]]; then
      echo "$item"
    fi
  done
}

pairs_raw="${PAIRS:-}"
timeframes_raw="${TIMEFRAMES:-}"
schedule_time="${SCHEDULE_TIME:-$default_schedule_time}"

pairs=()
if [[ -n "$pairs_raw" ]]; then
  while IFS= read -r item; do pairs+=("$item"); done < <(split_csv_or_space "$pairs_raw")
else
  pairs=("${allowed_pairs[@]}")
fi

timeframes=()
if [[ -n "$timeframes_raw" ]]; then
  while IFS= read -r item; do timeframes+=("$item"); done < <(split_csv_or_space "$timeframes_raw")
else
  timeframes=("${allowed_timeframes[@]}")
fi

if [[ ${#allowed_pairs[@]} -eq 0 ]]; then
  echo "Config has no allowed pairs." >&2
  exit 2
fi
if [[ ${#allowed_timeframes[@]} -eq 0 ]]; then
  echo "Config has no allowed timeframes." >&2
  exit 2
fi

for pair in "${pairs[@]}"; do
  ok=false
  for allowed in "${allowed_pairs[@]}"; do
    if [[ "$pair" == "$allowed" ]]; then
      ok=true
      break
    fi
  done
  if [[ "$ok" != "true" ]]; then
    echo "Invalid PAIRS: $pair. Allowed: ${allowed_pairs[*]}" >&2
    exit 2
  fi
done

for tf in "${timeframes[@]}"; do
  ok=false
  for allowed in "${allowed_timeframes[@]}"; do
    if [[ "$tf" == "$allowed" ]]; then
      ok=true
      break
    fi
  done
  if [[ "$ok" != "true" ]]; then
    echo "Invalid TIMEFRAMES: $tf. Allowed: ${allowed_timeframes[*]}" >&2
    exit 2
  fi
done

if [[ "$ACTION" == "schedule" || "$ACTION" == "validate" ]]; then
  if [[ -z "$schedule_time" || "$schedule_time" == "null" ]]; then
    echo "Missing SCHEDULE_TIME and no schedule_time in config." >&2
    exit 2
  fi
  if [[ -n "$default_schedule_time" && "$schedule_time" != "$default_schedule_time" ]]; then
    echo "Invalid SCHEDULE_TIME: $schedule_time. Allowed: $default_schedule_time" >&2
    exit 2
  fi
fi

if [[ "$ACTION" == "validate" ]]; then
  exit 0
fi

print_list() {
  local label="$1"
  shift
  local items=("$@")
  if [[ ${#items[@]} -eq 0 ]]; then
    echo "$label: <none>"
  else
    echo "$label: ${items[*]}"
  fi
}

if [[ "$ACTION" == "info" ]]; then
  echo "Config: $CONFIG"
  echo "Raw config:"
  jq '.' "$CONFIG"
  echo
  echo "Resolved parameters:"
  echo "Exchange: $exchange"
  print_list "Pairs" "${pairs[@]}"
  print_list "Timeframes" "${timeframes[@]}"
  if [[ -n "$schedule_time" && "$schedule_time" != "null" ]]; then
    echo "Schedule time: $schedule_time"
  else
    echo "Schedule time: <none>"
  fi
  exit 0
fi

args=()
for pair in "${pairs[@]}"; do
  args+=(--pair "$pair")
done
for tf in "${timeframes[@]}"; do
  args+=(--timeframe "$tf")
done
args+=(--exchange "$exchange")
if [[ "$ACTION" == "schedule" ]]; then
  args+=(--schedule-time "$schedule_time")
fi

printf "%s " "${args[@]}"
