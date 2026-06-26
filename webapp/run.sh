#!/bin/bash
# Run the Workflower webapp locally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <connection_name>"
    echo "Example: $0 U2C"
    echo ""
    echo "Available connections:"
    python3 -c "
import tomllib, os
paths = [os.path.expanduser('~/.snowflake/config.toml'),
         os.path.expanduser('~/Library/Application Support/snowflake/config.toml')]
for p in paths:
    if os.path.exists(p):
        cfg = tomllib.load(open(p, 'rb'))
        for c in cfg.get('connections', {}):
            print(f'  {c}')
" 2>/dev/null || echo "  (no connections found)"
    exit 1
fi

echo "=== Workflower Webapp ==="
echo "Connection: $1"
echo ""

cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Installing dependencies..."
    "$VENV_DIR/bin/pip" install -q -r requirements.txt
else
    "$VENV_DIR/bin/pip" install -q -r requirements.txt 2>/dev/null || {
        echo "Installing missing dependencies..."
        "$VENV_DIR/bin/pip" install -r requirements.txt
    }
fi

PORT=${PORT:-8000}
echo "Starting server on http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""

SNOWFLAKE_CONNECTION="$1" PORT="$PORT" "$VENV_DIR/bin/python3" server.py