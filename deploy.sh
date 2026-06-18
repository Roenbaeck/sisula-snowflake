#!/bin/bash
# Deploy sisula-snowflake to Snowflake
# Usage: ./deploy.sh <connection_name>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <connection_name>"
    echo "Example: $0 my_snowflake_conn"
    exit 1
fi

CONNECTION="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== sisula-snowflake deploy ==="
echo "Connection: $CONNECTION"
echo ""

snow sql -c "$CONNECTION" --enable-templating NONE -f "$SCRIPT_DIR/sql/deploy.sql"

echo ""
echo "=== Deploy complete ==="
