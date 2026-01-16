#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restarting Equities AI services..."

"$SCRIPT_DIR/stop.sh"
sleep 2
"$SCRIPT_DIR/start.sh"
