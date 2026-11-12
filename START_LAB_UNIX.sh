#!/bin/sh
set -eu
cd "$(dirname "$0")"
printf '%s\n' 'Decision Drift Lab — local only' 'Open http://127.0.0.1:8765/  | Stop with CTRL+C'
exec python3 -m http.server 8765 --bind 127.0.0.1 --directory docs
