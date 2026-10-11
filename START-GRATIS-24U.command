#!/bin/bash
set -eu
cd "$(dirname "$0")"
if command -v caffeinate >/dev/null 2>&1; then
 exec caffeinate -dims python3 start.py --tunnel "$@"
fi
exec python3 start.py --tunnel "$@"
