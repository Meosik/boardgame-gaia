#!/usr/bin/env bash
# Non-interactive Astra/Sol handoff supervisor; no permission bypass flags.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == "--background" ]]; then
    shift
    mkdir -p "$ROOT/handoff/logs"
    LOG="$ROOT/handoff/logs/$(date -u +%Y%m%dT%H%M%SZ)-supervisor-$$.log"
    nohup setsid python3 -u "$ROOT/scripts/handoff_loop.py" "$@" >"$LOG" 2>&1 </dev/null &
    exit 0
fi
exec python3 -u "$ROOT/scripts/handoff_loop.py" "$@"
